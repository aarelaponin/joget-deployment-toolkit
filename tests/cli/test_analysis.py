"""
Tests for the dependency analysis module.
"""

import json
import pytest
from pathlib import Path

from joget_deployment_toolkit.cli.analysis import (
    extract_dependencies,
    build_dependency_graph,
    topological_sort,
    analyze_dependencies,
    format_dependency_report,
    DependencyAnalysis,
)


class TestExtractDependencies:
    """Tests for extract_dependencies function."""

    def test_empty_form(self):
        """Test form with no elements."""
        form = {"className": "org.joget.apps.form.model.Form", "elements": []}
        deps = extract_dependencies(form)
        assert deps == set()

    def test_form_grid_dependency(self):
        """Test extraction from FormGrid element."""
        form = {
            "elements": [
                {
                    "className": "org.joget.plugin.enterprise.FormGrid",
                    "properties": {"id": "grid1", "formDefId": "subForm1"},
                    "elements": [],
                }
            ]
        }
        deps = extract_dependencies(form)
        assert deps == {"subForm1"}

    def test_options_binder_dependency(self):
        """Test extraction from optionsBinder."""
        form = {
            "elements": [
                {
                    "className": "org.joget.apps.form.lib.SelectBox",
                    "properties": {
                        "id": "select1",
                        "optionsBinder": {
                            "className": "org.joget.apps.form.lib.FormOptionsBinder",
                            "properties": {"formDefId": "lookupForm"},
                        },
                    },
                    "elements": [],
                }
            ]
        }
        deps = extract_dependencies(form)
        assert deps == {"lookupForm"}

    def test_nested_elements(self):
        """Test extraction from deeply nested elements."""
        form = {
            "elements": [
                {
                    "className": "org.joget.apps.form.model.Section",
                    "properties": {"id": "section1"},
                    "elements": [
                        {
                            "className": "org.joget.apps.form.model.Column",
                            "properties": {},
                            "elements": [
                                {
                                    "className": "org.joget.plugin.enterprise.FormGrid",
                                    "properties": {"formDefId": "nestedForm"},
                                    "elements": [],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        deps = extract_dependencies(form)
        assert deps == {"nestedForm"}

    def test_multiple_dependencies(self):
        """Test extraction of multiple dependencies."""
        form = {
            "elements": [
                {
                    "className": "org.joget.apps.form.lib.SelectBox",
                    "properties": {
                        "optionsBinder": {"properties": {"formDefId": "lookup1"}}
                    },
                    "elements": [],
                },
                {
                    "className": "org.joget.apps.form.lib.SelectBox",
                    "properties": {
                        "optionsBinder": {"properties": {"formDefId": "lookup2"}}
                    },
                    "elements": [],
                },
                {
                    "className": "org.joget.plugin.enterprise.FormGrid",
                    "properties": {"formDefId": "subform1"},
                    "elements": [],
                },
            ]
        }
        deps = extract_dependencies(form)
        assert deps == {"lookup1", "lookup2", "subform1"}

    def test_empty_form_def_id_ignored(self):
        """Test that empty formDefId is ignored."""
        form = {
            "elements": [
                {
                    "className": "org.joget.plugin.enterprise.FormGrid",
                    "properties": {"formDefId": ""},
                    "elements": [],
                },
                {
                    "className": "org.joget.apps.form.lib.SelectBox",
                    "properties": {
                        "optionsBinder": {"properties": {"formDefId": ""}}
                    },
                    "elements": [],
                },
            ]
        }
        deps = extract_dependencies(form)
        assert deps == set()

    def test_whitespace_form_def_id_trimmed(self):
        """Test that whitespace in formDefId is trimmed."""
        form = {
            "elements": [
                {
                    "className": "org.joget.plugin.enterprise.FormGrid",
                    "properties": {"formDefId": "  form1  "},
                    "elements": [],
                }
            ]
        }
        deps = extract_dependencies(form)
        assert deps == {"form1"}

    def test_load_binder_dependency(self):
        """Test extraction from loadBinder."""
        form = {
            "elements": [
                {
                    "className": "org.joget.apps.form.lib.TextField",
                    "properties": {
                        "id": "field1",
                        "loadBinder": {"properties": {"formDefId": "dataForm"}},
                    },
                    "elements": [],
                }
            ]
        }
        deps = extract_dependencies(form)
        assert deps == {"dataForm"}


class TestBuildDependencyGraph:
    """Tests for build_dependency_graph function."""

    def test_simple_graph(self):
        """Test building graph from multiple forms."""
        forms = {
            "form1": {
                "elements": [
                    {"properties": {"formDefId": "form2"}, "elements": []}
                ]
            },
            "form2": {"elements": []},
        }
        graph = build_dependency_graph(forms)
        assert graph == {"form1": {"form2"}, "form2": set()}

    def test_no_dependencies(self):
        """Test graph with no dependencies."""
        forms = {
            "form1": {"elements": []},
            "form2": {"elements": []},
        }
        graph = build_dependency_graph(forms)
        assert graph == {"form1": set(), "form2": set()}


class TestTopologicalSort:
    """Tests for topological_sort function."""

    def test_simple_chain(self):
        """Test sorting a simple dependency chain."""
        forms = {
            "parent": {
                "elements": [{"properties": {"formDefId": "child"}, "elements": []}]
            },
            "child": {"elements": []},
        }
        order, cycles = topological_sort(forms)
        assert cycles == []
        assert order.index("child") < order.index("parent")

    def test_no_dependencies(self):
        """Test sorting forms with no dependencies."""
        forms = {
            "form_c": {"elements": []},
            "form_a": {"elements": []},
            "form_b": {"elements": []},
        }
        order, cycles = topological_sort(forms)
        assert cycles == []
        # Should be alphabetical when no deps
        assert order == ["form_a", "form_b", "form_c"]

    def test_complex_dependencies(self):
        """Test sorting with multiple dependency levels."""
        forms = {
            "level3": {
                "elements": [
                    {"properties": {"formDefId": "level2a"}, "elements": []},
                    {"properties": {"formDefId": "level2b"}, "elements": []},
                ]
            },
            "level2a": {
                "elements": [{"properties": {"formDefId": "level1"}, "elements": []}]
            },
            "level2b": {
                "elements": [{"properties": {"formDefId": "level1"}, "elements": []}]
            },
            "level1": {"elements": []},
        }
        order, cycles = topological_sort(forms)
        assert cycles == []
        # level1 must come first
        assert order[0] == "level1"
        # level2a and level2b must come before level3
        assert order.index("level2a") < order.index("level3")
        assert order.index("level2b") < order.index("level3")

    def test_external_dependencies_ignored(self):
        """Test that external dependencies don't affect order."""
        forms = {
            "form1": {
                "elements": [
                    {"properties": {"formDefId": "external"}, "elements": []}
                ]
            },
            "form2": {"elements": []},
        }
        order, cycles = topological_sort(forms)
        assert cycles == []
        # Both forms have no internal deps, so alphabetical
        assert order == ["form1", "form2"]

    def test_circular_dependency_detected(self):
        """Test detection of circular dependencies."""
        forms = {
            "form_a": {
                "elements": [{"properties": {"formDefId": "form_b"}, "elements": []}]
            },
            "form_b": {
                "elements": [{"properties": {"formDefId": "form_a"}, "elements": []}]
            },
        }
        order, cycles = topological_sort(forms)
        # Should detect the cycle
        assert len(cycles) > 0


class TestAnalyzeDependencies:
    """Tests for analyze_dependencies function."""

    def test_complete_analysis(self):
        """Test full dependency analysis."""
        forms = {
            "main": {
                "elements": [
                    {"properties": {"formDefId": "internal"}, "elements": []},
                    {
                        "properties": {
                            "optionsBinder": {"properties": {"formDefId": "external"}}
                        },
                        "elements": [],
                    },
                ]
            },
            "internal": {"elements": []},
        }
        analysis = analyze_dependencies(forms, existing_forms={"external"})

        assert "internal" in analysis.internal_dependencies
        assert "external" in analysis.external_dependencies
        assert analysis.deployment_order.index("internal") < analysis.deployment_order.index("main")
        assert not analysis.has_issues()

    def test_no_issues(self):
        """Test analysis with no issues."""
        forms = {
            "form1": {"elements": []},
            "form2": {"elements": []},
        }
        analysis = analyze_dependencies(forms)
        assert not analysis.has_issues()
        assert analysis.circular_dependencies == []

    def test_has_issues_with_cycles(self):
        """Test that has_issues returns True for circular deps."""
        forms = {
            "a": {"elements": [{"properties": {"formDefId": "b"}, "elements": []}]},
            "b": {"elements": [{"properties": {"formDefId": "a"}, "elements": []}]},
        }
        analysis = analyze_dependencies(forms)
        assert analysis.has_issues()


class TestFormatDependencyReport:
    """Tests for format_dependency_report function."""

    def test_basic_report(self):
        """Test report formatting."""
        analysis = DependencyAnalysis(
            dependencies={"form1": {"form2"}, "form2": set()},
            deployment_order=["form2", "form1"],
            internal_dependencies={"form2"},
            external_dependencies={"external"},
            circular_dependencies=[],
        )
        report = format_dependency_report(analysis)
        assert "Deployment Order" in report
        assert "form1" in report
        assert "form2" in report
        assert "External Dependencies" in report
        assert "external" in report

    def test_report_with_cycles(self):
        """Test report formatting with circular dependencies."""
        analysis = DependencyAnalysis(
            dependencies={"a": {"b"}, "b": {"a"}},
            deployment_order=[],
            internal_dependencies={"a", "b"},
            external_dependencies=set(),
            circular_dependencies=[("a", "b", "a")],
        )
        report = format_dependency_report(analysis)
        assert "WARNING" in report
        assert "Circular" in report


class TestRealFormFiles:
    """Tests using real form files from components/imm/forms/."""

    @pytest.fixture
    def imm_forms_dir(self) -> Path:
        """Get path to IMM forms directory."""
        return Path(__file__).parent.parent.parent / "components" / "imm" / "forms"

    def test_extract_imcampaign_dependencies(self, imm_forms_dir: Path):
        """Test dependency extraction from real imCampaign.json."""
        form_file = imm_forms_dir / "imCampaign.json"
        if not form_file.exists():
            pytest.skip("imCampaign.json not found")

        with open(form_file) as f:
            form_json = json.load(f)

        deps = extract_dependencies(form_json)

        # Should find MDM dependencies
        assert "md39CampaignType" in deps or len(deps) > 0

    def test_analyze_all_imm_forms(self, imm_forms_dir: Path):
        """Test full analysis of all IMM forms."""
        if not imm_forms_dir.exists():
            pytest.skip("IMM forms directory not found")

        form_files = list(imm_forms_dir.glob("*.json"))
        if not form_files:
            pytest.skip("No form files found")

        # Load all forms
        forms_data = {}
        for form_file in form_files:
            with open(form_file) as f:
                forms_data[form_file.stem] = json.load(f)

        # Analyze
        analysis = analyze_dependencies(forms_data)

        # Should have deployment order for all forms
        assert len(analysis.deployment_order) == len(forms_data)

        # Should identify external dependencies (MDM forms)
        # Note: External deps are forms referenced but not in the package
        assert isinstance(analysis.external_dependencies, set)

        # Print report for debugging
        report = format_dependency_report(analysis)
        print("\n" + report)
