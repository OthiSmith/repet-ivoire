"""Calcul des coordonnées des courbes de notes (SVG dessiné dans le gabarit, sans bibliothèque JS)."""
from dataclasses import dataclass, field

WIDTH, HEIGHT = 320, 140
PAD_LEFT, PAD_RIGHT, PAD_TOP, PAD_BOTTOM = 28, 12, 10, 22


@dataclass
class Point:
    x: float
    y: float
    value: float
    label: str


@dataclass
class LineChart:
    title: str
    points: list = field(default_factory=list)
    width: int = WIDTH
    height: int = HEIGHT

    @property
    def polyline(self):
        return " ".join(f"{p.x:.1f},{p.y:.1f}" for p in self.points)

    @property
    def gridlines(self):
        """Repères à 0, 10 et 20 (10 = la moyenne)."""
        return [{"value": v, "y": _y(v), "is_average": v == 10} for v in (0, 10, 20)]

    @property
    def plot_left(self):
        return PAD_LEFT

    @property
    def plot_right(self):
        return self.width - PAD_RIGHT

    @property
    def average(self):
        return round(sum(p.value for p in self.points) / len(self.points), 2) if self.points else None

    @property
    def last(self):
        return self.points[-1] if self.points else None


def _y(value):
    plot_height = HEIGHT - PAD_TOP - PAD_BOTTOM
    return PAD_TOP + plot_height * (1 - value / 20)


def grade_charts(grades):
    """Un graphique par matière : notes sur 20 dans l'ordre chronologique."""
    by_subject = {}
    for grade in grades:
        by_subject.setdefault(grade.subject, []).append(grade)
    charts = []
    plot_width = WIDTH - PAD_LEFT - PAD_RIGHT
    for subject, items in by_subject.items():
        n = len(items)
        chart = LineChart(title=subject.name)
        for i, grade in enumerate(items):
            x = PAD_LEFT + (plot_width / 2 if n == 1 else plot_width * i / (n - 1))
            value = float(grade.on_twenty)
            # Date complète : « 11/10 » seul se lirait comme une note.
            score = f"{value:g}".replace(".", ",")
            chart.points.append(Point(x, _y(min(value, 20)), value,
                                      f"{grade.date:%d/%m/%Y} · {grade.get_kind_display()} : {score}/20"))
        charts.append(chart)
    return charts
