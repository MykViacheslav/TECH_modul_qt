import pytest

from src.domain.service_models import ServiceComponentDef
from src.utils.cost_utils import calc_material_and_work_costs


def test_calc_material_and_work_costs_basic():
    comps = [
        ServiceComponentDef(component_id="c1", service_id="S1", component_type="material", ref_id="M1", name="Mat1", quantity=2.0, unit="kg", estimated_cost=5.0),
        ServiceComponentDef(component_id="c2", service_id="S1", component_type="work", ref_id="W1", name="Work1", quantity=3.0, unit="h", estimated_cost=0.0),
        ServiceComponentDef(component_id="c3", service_id="S1", component_type="service", ref_id="S2", name="Svc2", quantity=1.0, unit="", estimated_cost=7.5),
    ]
    mat, hours = calc_material_and_work_costs(comps)
    assert mat == pytest.approx(5.0 + 7.5)
    assert hours == pytest.approx(3.0)


def test_calc_costs_empty():
    mat, hours = calc_material_and_work_costs([])
    assert mat == 0.0 and hours == 0.0
