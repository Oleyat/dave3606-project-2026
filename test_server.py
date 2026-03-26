import json
from server import app, get_next_sets_forward, get_next_sets_backward, get_set_and_inventory

class MockDB:
    def __init__(self, expected_query, expected_params, fake_rows): #what moch should expect and return
        self.expected_query = expected_query
        self.expected_params = expected_params
        self.fake_rows = fake_rows
        self.closed = False

    def execute_and_fetch_all(self, query, params=None): #check if query and params match what we expect, then return fake rows.
        assert query.strip() == self.expected_query.strip()
        assert params == self.expected_params
        return self.fake_rows

    def close(self): #checks if close is called 
        self.closed = True
      
def test_get_set_and_inventory():
    expected_query = """
        SELECT s.id, s.name, COALESCE(s.year::text, ''), s.category, s.preview_image_url, inv.brick_type_id, inv.color_id, inv.count, b.name, b.preview_image_url
        FROM lego_set s 
        LEFT JOIN lego_inventory inv ON s.id=inv.set_id 
        LEFT JOIN lego_brick b ON inv.brick_type_id = b.brick_type_id AND inv.color_id = b.color_id
        WHERE s.id = %s
    """

    fake_rows = [
        (1, "Set 1", "2020", "Category A", "url1", "100", "10", "2", "Brick A", "brick_url_a"),
        (1, "Set 1", "2020", "Category A", "url1", "101", "11", "3", "Brick B", "brick_url_b"),
    ]

    db = MockDB(expected_query, ("1",), fake_rows)
    result = get_set_and_inventory(db, "1")
    parsed = json.loads(result) #convert json string back to dict for easier assertions

    #assertions to check if the result is as expected
    assert parsed["set_id"] == "1"
    assert parsed["name"] == "Set 1"
    assert parsed["year"] == "2020"
    assert parsed["category"] == "Category A"
    assert parsed["preview_image_url"] == "url1"
    
    assert parsed["inventory"] == [
        {
            "brick_type_id": "100",
            "color_id": "10",
            "count": "2",
            "brick_name": "Brick A",
            "preview_image_url": "brick_url_a"
        },
        {
            "brick_type_id": "101",
            "color_id": "11",
            "count": "3",
            "brick_name": "Brick B",
            "preview_image_url": "brick_url_b"
        }
    ]   