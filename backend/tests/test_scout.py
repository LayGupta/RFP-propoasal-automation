"""test_scout.py — Scout service tests"""

from unittest.mock import patch, MagicMock


def test_build_queries_no_products():
    with patch("app.services.scout_service.supabase_client") as mock_sb:
        mock_sb.table.return_value.select.return_value.execute.return_value.data = []

        from app.services.scout_service import _build_queries_from_inventory
        queries = _build_queries_from_inventory()
        assert len(queries) == 1
        assert queries[0]["category"] == "Default"


def test_build_queries_from_products():
    with patch("app.services.scout_service.supabase_client") as mock_sb:
        mock_sb.table.return_value.select.return_value.execute.return_value.data = [
            {"insulation_type": "XLPE", "voltage_rating": 1100, "conductor_material": "copper", "category": "HV"},
            {"insulation_type": "PVC", "voltage_rating": 600, "conductor_material": "aluminium", "category": "LV"},
        ]

        from app.services.scout_service import _build_queries_from_inventory
        queries = _build_queries_from_inventory()
        assert len(queries) == 2
        assert any("copper" in q["category"].lower() for q in queries)
