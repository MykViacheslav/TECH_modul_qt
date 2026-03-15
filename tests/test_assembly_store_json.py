from src.domain.assembly_models import AssemblyModuleItemDef, FurnitureAssemblyDef
from src.domain.module_models import ModuleDef
from src.storage.assembly_store_json import AssemblyStoreJson


def test_assembly_store_json_roundtrip(tmp_path):
    store = AssemblyStoreJson(path=tmp_path / "assemblies.json")

    assembly = FurnitureAssemblyDef(
        name="KOMPLET_TEST",
        wall_name="SCIANA_A",
        client_name="Klient Test",
        order_name="ORD-700",
        worker_name="Jan Monter",
        width_mm=3200.0,
        height_mm=2600.0,
        depth_mm=600.0,
        items=[
            AssemblyModuleItemDef(
                source_name="MOD_1",
                instance_name="MOD_1",
                module=ModuleDef(name="MOD_1", width_mm=800.0, depth_mm=500.0, height_mm=720.0),
            )
        ],
    )

    result = store.save_new(assembly)
    assert result.ok

    loaded = store.get("KOMPLET_TEST")
    assert loaded is not None
    assert loaded.wall_name == "SCIANA_A"
    assert loaded.client_name == "Klient Test"
    assert loaded.order_name == "ORD-700"
    assert loaded.worker_name == "Jan Monter"
    assert len(loaded.items) == 1
    assert loaded.items[0].source_name == "MOD_1"
