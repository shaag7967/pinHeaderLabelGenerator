"""Geometry, label placement, label layout and page layout (no Qt needed)."""

from itertools import pairwise

import pytest

from pin_header_label.layout import PAGE_HEIGHT_MM, PAGE_MARGIN_MM, PAGE_WIDTH_MM, PageLayout, Point, Rect
from pin_header_label.layout.label_layout import LEFT, MM_PER_PT, REFERENCE_PX, RIGHT
from pin_header_label.layout.placement import place_labels
from pin_header_label.model import ColorStyle, LeaderMode, Numbering, Project, SideMode

from conftest import MonospaceMetrics, make_layout


class TestGeometry:
    def test_edges(self):
        rect = Rect(1, 2, 3, 4)
        assert (rect.left, rect.top, rect.right, rect.bottom) == (1, 2, 4, 6)

    def test_united_and_adjusted(self):
        rect = Rect(0, 0, 2, 2).united(Rect(1, -1, 3, 1))
        assert rect == Rect(0, -1, 4, 3)
        assert rect.adjusted(-1, -1, 1, 1) == Rect(-1, -2, 6, 5)

    def test_bounding(self):
        assert Rect.bounding([Point(1, 5), Point(-2, 3), Point(0, 7)]) == Rect(-2, 3, 3, 4)
        assert Rect.bounding([]) == Rect()

    def test_contains_rect(self):
        assert Rect(0, 0, 10, 10).contains_rect(Rect(1, 1, 2, 2))
        assert not Rect(0, 0, 10, 10).contains_rect(Rect(9, 9, 2, 2))


class TestPlacement:
    def test_no_overlap_keeps_positions(self):
        assert place_labels([0.0, 5.0, 10.0], 2.0) == [0.0, 5.0, 10.0]

    def test_overlapping_pair_is_centered(self):
        assert place_labels([5.0, 5.0], 2.0) == pytest.approx([4.0, 6.0])

    def test_cluster_merging_keeps_order_and_distance(self):
        desired = [0.0, 0.5, 1.0, 1.5, 10.0]
        placed = place_labels(desired, 1.0)
        assert all(b - a >= 1.0 - 1e-9 for a, b in pairwise(placed))
        # the cluster is centered on its pins
        assert sum(placed[:4]) / 4 == pytest.approx(sum(desired[:4]) / 4)
        assert placed[4] == 10.0

    def test_empty(self):
        assert place_labels([], 1.0) == []


def _boxes_overlap(a: Rect, b: Rect) -> bool:
    return a.left < b.right and b.left < a.right and a.top < b.bottom and b.top < a.bottom


class TestLabelLayout:
    def test_scales_follow_font_size(self):
        layout = make_layout(Project(font_pt=7.2))
        assert layout.text_scale == pytest.approx(7.2 * MM_PER_PT / REFERENCE_PX)
        assert layout.number_scale == pytest.approx(layout.text_scale * 0.75)

    def test_header_size(self):
        layout = make_layout(Project(rows=10, cols=2, pitch=2.54))
        assert layout.width == pytest.approx(5.08)
        assert layout.height == pytest.approx(25.4)

    def test_only_labeled_pins_get_labels(self, small_project):
        layout = make_layout(small_project)
        assert sorted((g.row, g.col) for g in layout.labels) == [(0, 0), (0, 1), (1, 0), (3, 1)]

    def test_sides_of_two_row_header(self, small_project):
        layout = make_layout(small_project)
        for label in layout.labels:
            assert label.side == (LEFT if label.col == 0 else RIGHT)
            if label.side == LEFT:
                assert label.box.right <= 0.0
            else:
                assert label.box.left >= layout.width

    @pytest.mark.parametrize(
        ("mode", "expected"),
        [(SideMode.RIGHT, [RIGHT] * 4), (SideMode.LEFT, [LEFT] * 4), (SideMode.ALTERNATE, [LEFT, RIGHT] * 2)],
    )
    def test_sides_of_single_row_header(self, mode, expected):
        project = Project(rows=4, cols=1, side_mode=mode)
        for row in range(4):
            project.pin(row, 0).label = f"P{row}"
        layout = make_layout(project)
        assert [g.side for g in sorted(layout.labels, key=lambda g: g.row)] == expected

    def test_small_font_needs_no_shifting(self, small_project):
        small_project.font_pt = 5.0
        layout = make_layout(small_project)
        assert layout.shifted_count == 0
        assert layout.fanned_sides == []
        assert all(not g.leader for g in layout.labels)  # leaders only when needed

    def test_leaders_always(self, small_project):
        small_project.leaders = LeaderMode.ALWAYS
        layout = make_layout(small_project)
        assert all(len(g.leader) == 2 for g in layout.labels)

    def test_dense_labels_are_fanned_out_without_overlap(self):
        project = Project(rows=10, cols=2, pitch=1.27, font_pt=10)
        for row, col, pin in project.iter_pins():
            pin.label = f"SIG{row}{col}"
        layout = make_layout(project)
        assert layout.shifted_count > 0
        assert sorted(layout.fanned_sides) == [LEFT, RIGHT]
        for side in (LEFT, RIGHT):
            boxes = sorted((g.box for g in layout.labels if g.side == side), key=lambda b: b.top)
            for a, b in pairwise(boxes):
                assert not _boxes_overlap(a, b)
                assert b.top - a.bottom >= layout.BOX_GAP - 1e-9
        for label in layout.labels:
            if label.shifted:
                assert len(label.leader) == 4
                assert label.leader[0].y == pytest.approx(label.pin.y)
                assert label.leader[-1].y == pytest.approx(label.center_y)

    def test_text_is_vertically_centered_in_box(self, small_project):
        layout = make_layout(small_project)
        scale = layout.text_scale
        for label in layout.labels:
            ink_top = label.baseline + MonospaceMetrics.TOP * scale
            ink_bottom = label.baseline + MonospaceMetrics.BOTTOM * scale
            assert (ink_top + ink_bottom) / 2 == pytest.approx(label.box.top + label.box.height / 2)

    def test_text_style_has_no_padding(self, small_project):
        small_project.color_style = ColorStyle.TEXT
        layout = make_layout(small_project)
        assert layout.pad_h == layout.pad_v == 0.0

    def test_pin_numbers(self, small_project):
        small_project.numbering = Numbering.ZIGZAG
        layout = make_layout(small_project)
        numbers = {(g.row, g.col): g.number for g in layout.labels}
        assert numbers == {(0, 0): "1", (0, 1): "2", (1, 0): "3", (3, 1): "8"}
        for label in layout.labels:
            assert label.box.left <= label.text_x
            assert label.box.left <= label.number_x <= label.box.right

    def test_bbox_contains_everything(self, small_project):
        small_project.title = "J1"
        small_project.pin1_marker = True
        layout = make_layout(small_project)
        inner = layout.bbox.adjusted(
            layout.CUT_MARGIN, layout.CUT_MARGIN, -layout.CUT_MARGIN, -layout.CUT_MARGIN
        )
        assert inner.contains_rect(layout.header_rect)
        for label in layout.labels:
            assert inner.contains_rect(label.box)
        assert layout.pin1_marker is not None
        assert inner.contains_rect(Rect.bounding(layout.pin1_marker))
        assert layout.title == "J1"
        assert layout.title_origin.y < 0  # above the header

    def test_empty_project(self):
        layout = make_layout(Project(rows=2))
        assert layout.labels == []
        assert layout.bbox == layout.header_rect.adjusted(-2, -2, 2, 2)


class TestPageLayout:
    def test_single_copy_at_margin(self):
        page = PageLayout(30, 40, copies=1, scale_bar=True)
        assert page.positions == [Point(PAGE_MARGIN_MM, page.content_top)]
        assert page.fits_all

    def test_scale_bar_moves_content_down(self):
        assert PageLayout(30, 40, 1, True).content_top > PageLayout(30, 40, 1, False).content_top

    def test_copies_wrap_into_rows(self):
        page = PageLayout(80, 40, copies=4, scale_bar=False)
        assert page.placed == 4
        xs = [p.x for p in page.positions]
        ys = [p.y for p in page.positions]
        assert xs[0] == xs[2] and ys[0] == ys[1] and ys[2] > ys[0]
        for p in page.positions:
            assert p.x + 80 <= PAGE_WIDTH_MM - PAGE_MARGIN_MM + 1e-6

    def test_too_many_copies(self):
        page = PageLayout(90, 120, copies=10, scale_bar=True)
        assert page.placed < 10
        assert not page.fits_all
        for p in page.positions:
            assert p.y + 120 <= PAGE_HEIGHT_MM

    def test_sheet_larger_than_page(self):
        assert PageLayout(300, 40, copies=1, scale_bar=True).placed == 0
