"""Tests du suivi Premium : souscription, accès, programme, séances, assiduité, notes, rapport."""
from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone

from catalog.models import Level, Subject
from core.testing import TempMediaTestCase, make_admin, make_tutor, make_user
from locations.models import Commune
from notifications.models import Notification
from premium import services
from premium.models import CurriculumUnit, Grade, PlanItem, Session, Subscription
from premium.services import PremiumError, add_months
from tutoring.models import TutoringRequest
from tutoring.services import choose_proposal, propose_tutor, respond_to_proposal


class PremiumTestCase(TempMediaTestCase):
    """Une mise en relation confirmée : parent, enfant en 3e à Cocody, répétiteur de maths choisi."""

    def setUp(self):
        self.admin = make_admin()
        self.parent = make_user()
        self.tutor = make_tutor(level="3e", commune="cocody", subjects=("mathematiques",))
        self.maths = Subject.objects.get(slug="mathematiques")
        self.request = TutoringRequest.objects.create(
            parent=self.parent, child_first_name="Yao", level=Level.objects.get(slug="3e"),
            commune=Commune.objects.get(slug="cocody"), neighborhood="Angré", availability="Soir",
            sessions_per_week=2,
        )
        self.request.subjects.add(self.maths)
        proposal = propose_tutor(self.request, self.tutor, self.admin)
        respond_to_proposal(proposal, self.tutor.user, accept=True)
        choose_proposal(proposal, self.parent)
        self.request.refresh_from_db()

    def active_subscription(self, months=1):
        subscription = services.request_premium(self.request, self.parent, months)
        services.activate(subscription, self.admin, months, amount=5000, payment_method="WAVE")
        return subscription


class AddMonthsTests(TempMediaTestCase):
    def test_end_of_month_is_clamped(self):
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(add_months(date(2026, 11, 15), 3), date(2027, 2, 15))


class SubscriptionTests(PremiumTestCase):
    def test_parent_requests_then_admin_activates(self):
        self.client.force_login(self.parent)
        self.client.post(reverse("premium:offer", args=[self.request.pk]), {"months": 3})
        subscription = Subscription.objects.get()
        self.assertEqual(subscription.status, Subscription.Status.REQUESTED)
        self.assertTrue(Notification.objects.filter(user=self.admin, title__contains="Premium").exists())

        # Pas encore actif : le suivi renvoie vers l'offre.
        response = self.client.get(reverse("premium:tracking", args=[subscription.pk]))
        self.assertRedirects(response, reverse("premium:offer", args=[self.request.pk]))

        self.client.force_login(self.admin)
        self.client.post(reverse("backoffice:premium_detail", args=[subscription.pk]),
                         {"months": 3, "amount": 15000, "payment_method": "ORANGE", "payment_reference": "OM123"})
        subscription.refresh_from_db()
        self.assertTrue(subscription.is_current)
        self.assertEqual(subscription.starts_on, timezone.localdate())
        self.assertEqual(subscription.ends_on, add_months(timezone.localdate(), 3) - timedelta(days=1))
        self.assertTrue(Notification.objects.filter(user=self.parent, title__contains="actif").exists())
        self.assertTrue(Notification.objects.filter(user=self.tutor.user, title__contains="Premium").exists())

    def test_extension_follows_current_period(self):
        subscription = self.active_subscription(months=1)
        first_end = subscription.ends_on
        services.activate(subscription, self.admin, 3)
        self.assertEqual(subscription.ends_on, add_months(first_end + timedelta(days=1), 3) - timedelta(days=1))

    def test_premium_requires_a_match(self):
        other = TutoringRequest.objects.create(
            parent=self.parent, child_first_name="Awa", level=Level.objects.get(slug="cm2"),
            commune=Commune.objects.get(slug="cocody"), neighborhood="Angré", availability="Soir")
        with self.assertRaises(PremiumError):
            services.request_premium(other, self.parent, 1)

    def test_other_parent_cannot_subscribe(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(reverse("premium:offer", args=[self.request.pk])).status_code, 404)

    def test_expired_subscription_is_read_only(self):
        subscription = self.active_subscription()
        Subscription.objects.filter(pk=subscription.pk).update(
            starts_on=timezone.localdate() - timedelta(days=60), ends_on=timezone.localdate() - timedelta(days=1))
        self.client.force_login(self.tutor.user)
        self.assertEqual(self.client.get(reverse("premium:tracking", args=[subscription.pk])).status_code, 200)
        response = self.client.get(reverse("premium:session_create", args=[subscription.pk]))
        self.assertRedirects(response, reverse("premium:tracking", args=[subscription.pk]))


class AccessTests(PremiumTestCase):
    def test_roles(self):
        subscription = self.active_subscription()
        url = reverse("premium:tracking", args=[subscription.pk])
        for user, expected in [(self.parent, 200), (self.tutor.user, 200), (self.admin, 200),
                               (make_user(), 404), (make_tutor().user, 404)]:
            with self.subTest(role=user.role, expected=expected):
                self.client.force_login(user)
                self.assertEqual(self.client.get(url).status_code, expected)

    def test_parent_cannot_declare_sessions(self):
        subscription = self.active_subscription()
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(reverse("premium:session_create", args=[subscription.pk])).status_code, 403)

    def test_tutor_cannot_confirm_sessions(self):
        subscription = self.active_subscription()
        session = Session.objects.create(subscription=subscription, date=timezone.localdate(), content="x")
        self.client.force_login(self.tutor.user)
        response = self.client.post(reverse("premium:session_respond", args=[session.pk]), {"decision": "confirm"})
        self.assertEqual(response.status_code, 404)


class PlanTests(PremiumTestCase):
    def test_import_reference_program_once(self):
        subscription = self.active_subscription()
        level = Level.objects.get(slug="3e")
        for i, title in enumerate(["Calcul littéral", "Théorème de Thalès"], 1):
            CurriculumUnit.objects.create(level=level, subject=self.maths, title=title, order=i)
        CurriculumUnit.objects.create(level=level, subject=Subject.objects.get(slug="anglais"), title="Hors sujet")
        self.assertEqual(services.import_reference_program(subscription), 2)
        self.assertEqual(services.import_reference_program(subscription), 0)  # pas de doublons

    def test_progress_by_subject(self):
        subscription = self.active_subscription()
        items = [PlanItem.objects.create(subscription=subscription, subject=self.maths, title=f"Chap {i}") for i in range(4)]
        services.set_plan_item_status(items[0], PlanItem.Status.ACQUIRED)
        services.set_plan_item_status(items[1], PlanItem.Status.IN_PROGRESS)
        row = services.progress_by_subject(subscription)[0]
        self.assertEqual((row["total"], row["ACQUIRED"], row["percent"]), (4, 1, 25))
        items[0].refresh_from_db()
        self.assertIsNotNone(items[0].acquired_at)

    def test_tutor_manages_plan_through_page(self):
        subscription = self.active_subscription()
        self.client.force_login(self.tutor.user)
        url = reverse("premium:plan", args=[subscription.pk])
        self.client.post(url, {"action": "add", "subject": self.maths.pk, "title": "Racines carrées"})
        item = PlanItem.objects.get()
        self.client.post(url, {"action": "status", "item": item.pk, "status": "ACQUIRED"})
        item.refresh_from_db()
        self.assertEqual(item.status, PlanItem.Status.ACQUIRED)

    def test_parent_cannot_edit_plan(self):
        subscription = self.active_subscription()
        self.client.force_login(self.parent)
        response = self.client.post(reverse("premium:plan", args=[subscription.pk]),
                                    {"action": "add", "subject": self.maths.pk, "title": "x"})
        self.assertEqual(response.status_code, 403)


class SessionTests(PremiumTestCase):
    def declare(self, subscription, **data):
        self.client.force_login(self.tutor.user)
        payload = {"date": timezone.localdate().isoformat(), "duration_minutes": 90, "status": "DONE",
                   "content": "Exercices de Thalès", "engagement": 4}
        payload.update(data)
        return self.client.post(reverse("premium:session_create", args=[subscription.pk]), payload)

    def test_declared_session_is_confirmed_by_parent(self):
        subscription = self.active_subscription()
        self.declare(subscription)
        session = Session.objects.get()
        self.assertTrue(session.awaits_parent)
        self.assertTrue(Notification.objects.filter(user=self.parent, title__contains="à confirmer").exists())

        self.client.force_login(self.parent)
        self.client.post(reverse("premium:session_respond", args=[session.pk]), {"decision": "confirm"})
        session.refresh_from_db()
        self.assertEqual(session.parent_status, Session.ParentStatus.CONFIRMED)

    def test_future_date_rejected(self):
        subscription = self.active_subscription()
        response = self.declare(subscription, date=(timezone.localdate() + timedelta(days=1)).isoformat())
        self.assertContains(response, "dans le futur")
        self.assertFalse(Session.objects.exists())

    def test_tutor_cannot_declare_himself_absent(self):
        subscription = self.active_subscription()
        response = self.declare(subscription, status="TUTOR_ABSENT")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Session.objects.exists())

    def test_disputed_session_counts_as_absence_and_alerts_admins(self):
        subscription = self.active_subscription()
        for _ in range(2):
            session = Session.objects.create(subscription=subscription, date=timezone.localdate(), content="x")
            services.respond_to_session(session, self.parent, confirmed=False, issue="TUTOR_ABSENT")
        stats = services.attendance_stats(subscription)
        self.assertEqual(stats["tutor_absences"], 2)
        self.assertEqual(stats["held"], 0)
        self.assertTrue(Notification.objects.filter(user=self.admin, title__contains="Absences répétées").exists())

    def test_parent_reports_missed_session(self):
        subscription = self.active_subscription()
        self.client.force_login(self.parent)
        self.client.post(reverse("premium:missed_session", args=[subscription.pk]),
                         {"date": timezone.localdate().isoformat(), "comment": "Pas venu"})
        session = Session.objects.get()
        self.assertTrue(session.tutor_was_absent)
        self.assertTrue(Notification.objects.filter(user=self.tutor.user, title__contains="Absence").exists())

    def test_attendance_stats(self):
        subscription = self.active_subscription()
        Subscription.objects.filter(pk=subscription.pk).update(starts_on=timezone.localdate() - timedelta(days=13))
        subscription.refresh_from_db()
        Session.objects.create(subscription=subscription, date=timezone.localdate(), duration_minutes=90,
                               parent_status="CONFIRMED", engagement=4)
        Session.objects.create(subscription=subscription, date=timezone.localdate(), duration_minutes=60, engagement=2)
        Session.objects.create(subscription=subscription, date=timezone.localdate(), status="CHILD_ABSENT")
        stats = services.attendance_stats(subscription)
        self.assertEqual(stats["held"], 2)
        self.assertEqual(stats["confirmed"], 1)
        self.assertEqual(stats["hours"], 2.5)
        self.assertEqual(stats["expected"], 4)  # 2 semaines × 2 séances
        self.assertEqual(stats["rate"], 50)
        self.assertEqual(stats["child_absences"], 1)
        self.assertEqual(stats["engagement"], 3)


class GradeAndReportTests(PremiumTestCase):
    def test_grade_cannot_exceed_out_of(self):
        subscription = self.active_subscription()
        self.client.force_login(self.parent)
        response = self.client.post(reverse("premium:grade_create", args=[subscription.pk]), {
            "subject": self.maths.pk, "date": timezone.localdate().isoformat(), "kind": "EXAM",
            "score": "25", "out_of": 20})
        self.assertContains(response, "ne peut pas dépasser")

    def test_tracking_page_draws_grade_chart(self):
        subscription = self.active_subscription()
        for i, score in enumerate(["8.5", "11", "14"]):
            Grade.objects.create(subscription=subscription, subject=self.maths, score=score,
                                 date=timezone.localdate() - timedelta(days=10 - i))
        Grade.objects.create(subscription=subscription, subject=self.maths, score=7, out_of=10,
                             date=timezone.localdate())  # 7/10 = 14/20
        self.client.force_login(self.parent)
        response = self.client.get(reverse("premium:tracking", args=[subscription.pk]))
        self.assertContains(response, "<polyline")
        self.assertContains(response, "Moyenne 11,88/20")
        # Coordonnées SVG au format point (et non virgule française).
        self.assertNotRegex(response.content.decode(), r'cy="\d+,\d')

    def test_monthly_report(self):
        subscription = self.active_subscription()
        item = PlanItem.objects.create(subscription=subscription, subject=self.maths, title="Thalès")
        services.set_plan_item_status(item, PlanItem.Status.ACQUIRED)
        self.client.force_login(self.parent)
        response = self.client.get(reverse("premium:report", args=[subscription.pk]),
                                   {"mois": timezone.localdate().strftime("%Y-%m")})
        self.assertContains(response, "Thalès")
        self.assertContains(response, "Imprimer")

    def test_report_ignores_bad_month(self):
        subscription = self.active_subscription()
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(reverse("premium:report", args=[subscription.pk]), {"mois": "abc"}).status_code, 200)

    def test_replacement_request_notifies_admins(self):
        subscription = self.active_subscription()
        self.client.force_login(self.parent)
        self.client.post(reverse("premium:replacement", args=[subscription.pk]), {"message": "Toujours en retard"})
        self.assertTrue(Notification.objects.filter(user=self.admin, title__contains="PRIORITAIRE").exists())


class BackofficeCurriculumTests(PremiumTestCase):
    def test_admin_adds_chapters_one_per_line(self):
        self.client.force_login(self.admin)
        level = Level.objects.get(slug="3e")
        self.client.post(reverse("backoffice:curriculum"), {
            "level": level.pk, "subject": self.maths.pk, "titles": "Calcul littéral\n\nThalès\n", "term": "T1"})
        self.assertEqual(list(CurriculumUnit.objects.values_list("title", flat=True)), ["Calcul littéral", "Thalès"])

    def test_curriculum_reserved_to_admins(self):
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(reverse("backoffice:curriculum")).status_code, 403)
