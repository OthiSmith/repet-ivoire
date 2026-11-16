"""Tests du parcours complet de mise en relation."""
from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from catalog.models import Level, Subject
from core.testing import TempMediaTestCase, make_admin, make_tutor, make_user
from locations.models import Commune
from notifications.models import Notification
from tutoring.models import Proposal, TutoringRequest
from tutoring.services import (
    ActionError,
    cancel_request,
    choose_proposal,
    expire_overdue_proposals,
    propose_tutor,
    respond_to_proposal,
    suggest_tutors,
)
from tutors.models import TutorProfile


class MatchingTestCase(TempMediaTestCase):
    def setUp(self):
        self.admin = make_admin()
        self.parent = make_user()
        self.tutor = make_tutor(level="3e", commune="cocody", subjects=("mathematiques", "physique-chimie"))
        self.request = TutoringRequest.objects.create(
            parent=self.parent, child_first_name="Yao", level=Level.objects.get(slug="3e"),
            commune=Commune.objects.get(slug="cocody"), neighborhood="Riviera 2",
            availability="Mardi et jeudi 17 h", sessions_per_week=2,
        )
        self.request.subjects.add(Subject.objects.get(slug="mathematiques"))


class RequestCreationTests(TempMediaTestCase):
    def test_parent_creates_request_and_admins_are_notified(self):
        admin = make_admin()
        parent = make_user()
        self.client.force_login(parent)
        response = self.client.post(reverse("tutoring:request_create"), {
            "child_first_name": "Aya", "level": Level.objects.get(slug="cm2").pk,
            "subjects": [Subject.objects.get(slug="francais").pk],
            "commune": Commune.objects.get(slug="yopougon").pk, "neighborhood": "Sideci",
            "sessions_per_week": 3, "availability": "Samedi matin",
        })
        tutoring_request = TutoringRequest.objects.get()
        self.assertRedirects(response, reverse("tutoring:request_detail", args=[tutoring_request.pk]))
        self.assertEqual(tutoring_request.parent, parent)
        self.assertTrue(Notification.objects.filter(user=admin, title__contains="Nouvelle demande").exists())

    def test_tutor_cannot_create_request(self):
        self.client.force_login(make_tutor().user)
        self.assertEqual(self.client.get(reverse("tutoring:request_create")).status_code, 403)


class SuggestionTests(MatchingTestCase):
    def test_matching_tutor_is_suggested(self):
        self.assertIn(self.tutor, suggest_tutors(self.request))

    def test_non_matching_tutors_are_excluded(self):
        other_commune = make_tutor(commune="abobo")
        other_level = make_tutor(level="cp1")
        other_subject = make_tutor(subjects=("anglais",))
        not_verified = make_tutor(status=TutorProfile.Status.PENDING)
        unavailable = make_tutor()
        unavailable.is_available = False
        unavailable.save()
        suggestions = list(suggest_tutors(self.request))
        for tutor in [other_commune, other_level, other_subject, not_verified, unavailable]:
            self.assertNotIn(tutor, suggestions)

    def test_already_proposed_tutor_is_excluded(self):
        propose_tutor(self.request, self.tutor, self.admin)
        self.assertNotIn(self.tutor, suggest_tutors(self.request))


class FullFlowTests(MatchingTestCase):
    def test_propose_accept_choose(self):
        proposal = propose_tutor(self.request, self.tutor, self.admin)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, TutoringRequest.Status.SEARCHING)
        self.assertTrue(Notification.objects.filter(user=self.tutor.user).exists())

        # Avant le choix, le répétiteur ne voit ni le nom ni le téléphone du parent.
        self.client.force_login(self.tutor.user)
        page = self.client.get(reverse("tutoring:tutor_proposal", args=[proposal.pk]))
        self.assertNotContains(page, self.parent.phone)
        self.assertNotContains(page, "Riviera 2")

        self.client.post(reverse("tutoring:tutor_proposal", args=[proposal.pk]), {"decision": "accept", "message": "Disponible !"})
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, Proposal.Status.ACCEPTED)

        # Le parent voit le profil, mais pas encore les coordonnées.
        self.client.force_login(self.parent)
        page = self.client.get(reverse("tutoring:request_detail", args=[self.request.pk]))
        self.assertContains(page, "Disponible !")
        self.assertNotContains(page, self.tutor.user.phone)

        self.client.post(reverse("tutoring:proposal_choose", args=[proposal.pk]))
        self.request.refresh_from_db()
        proposal.refresh_from_db()
        self.assertEqual(self.request.status, TutoringRequest.Status.MATCHED)
        self.assertEqual(proposal.status, Proposal.Status.CHOSEN)

        # Après le choix, chacun voit les coordonnées de l'autre.
        page = self.client.get(reverse("tutoring:request_detail", args=[self.request.pk]))
        self.assertContains(page, self.tutor.user.phone)
        self.client.force_login(self.tutor.user)
        page = self.client.get(reverse("tutoring:tutor_proposal", args=[proposal.pk]))
        self.assertContains(page, self.parent.phone)
        self.assertContains(page, "Riviera 2")

    def test_other_proposals_are_closed_when_one_is_chosen(self):
        other = make_tutor()
        chosen = propose_tutor(self.request, self.tutor, self.admin)
        not_chosen = propose_tutor(self.request, other, self.admin)
        respond_to_proposal(chosen, self.tutor.user, accept=True)
        respond_to_proposal(not_chosen, other.user, accept=True)
        choose_proposal(chosen, self.parent)
        not_chosen.refresh_from_db()
        self.assertEqual(not_chosen.status, Proposal.Status.NOT_CHOSEN)


class RuleTests(MatchingTestCase):
    @override_settings(MAX_PROPOSALS_PER_ROUND=1)
    def test_max_active_proposals(self):
        propose_tutor(self.request, self.tutor, self.admin)
        with self.assertRaises(ActionError):
            propose_tutor(self.request, make_tutor(), self.admin)

    def test_unverified_tutor_cannot_be_proposed(self):
        with self.assertRaises(ActionError):
            propose_tutor(self.request, make_tutor(status=TutorProfile.Status.PENDING), self.admin)

    def test_parent_cannot_choose_pending_proposal(self):
        proposal = propose_tutor(self.request, self.tutor, self.admin)
        with self.assertRaises(ActionError):
            choose_proposal(proposal, self.parent)

    def test_other_parent_cannot_choose(self):
        proposal = propose_tutor(self.request, self.tutor, self.admin)
        respond_to_proposal(proposal, self.tutor.user, accept=True)
        intruder = make_user()
        self.client.force_login(intruder)
        response = self.client.post(reverse("tutoring:proposal_choose", args=[proposal.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get(reverse("tutoring:request_detail", args=[self.request.pk])).status_code, 404)

    def test_other_tutor_cannot_respond(self):
        proposal = propose_tutor(self.request, self.tutor, self.admin)
        self.client.force_login(make_tutor().user)
        self.assertEqual(self.client.get(reverse("tutoring:tutor_proposal", args=[proposal.pk])).status_code, 404)

    def test_overdue_proposals_expire(self):
        proposal = propose_tutor(self.request, self.tutor, self.admin)
        Proposal.objects.filter(pk=proposal.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        proposal.refresh_from_db()
        with self.assertRaises(ActionError):
            respond_to_proposal(proposal, self.tutor.user, accept=True)
        self.assertEqual(expire_overdue_proposals(), 1)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, Proposal.Status.EXPIRED)

    def test_cancel_withdraws_active_proposals(self):
        proposal = propose_tutor(self.request, self.tutor, self.admin)
        cancel_request(self.request, self.parent)
        proposal.refresh_from_db()
        self.assertEqual(self.request.status, TutoringRequest.Status.CANCELLED)
        self.assertEqual(proposal.status, Proposal.Status.WITHDRAWN)
