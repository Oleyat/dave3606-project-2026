import json
import gzip
from server import app, get_next_sets_forward, get_next_sets_backward, get_set_and_inventory, encode_page_html, serialize_set_to_binary_data

class MockDB:
    def __init__(self, expected_query, expected_params, fake_rows): #what moch should expect and return
        self.expected_query = expected_query
        self.expected_params = expected_params
        self.fake_rows = fake_rows
        self.closed = False

    def normalize_sql(self, sql): #means the querys dont have to be identically formatted
        return " ".join(sql.split())

    def execute_and_fetch_all(self, query, params=None): #check if query and params match what we expect, then return fake rows.
        assert self.normalize_sql(query) == self.normalize_sql(self.expected_query)
        assert params == self.expected_params
        return self.fake_rows
      
def test_get_set_and_inventory(): #checks if get_set_and_inventory returns correct json string
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

def test_null_get_set_and_inventory(): #checks if get_set_and_inventory handles null values correctly
    expected_query = """
        SELECT s.id, s.name, COALESCE(s.year::text, ''), s.category, s.preview_image_url, inv.brick_type_id, inv.color_id, inv.count, b.name, b.preview_image_url
        FROM lego_set s 
        LEFT JOIN lego_inventory inv ON s.id=inv.set_id 
        LEFT JOIN lego_brick b ON inv.brick_type_id = b.brick_type_id AND inv.color_id = b.color_id
        WHERE s.id = %s
    """

    fake_rows = [
        (2, "Set 2", "", None, None, None, None, None, None, None), #variables that can be None (python null) are represented as empty strings, year none is handled in query
    ]

    db = MockDB(expected_query, ("2",), fake_rows)
    result = get_set_and_inventory(db, "2")
    parsed = json.loads(result)

    assert parsed["set_id"] == "2"
    assert parsed["name"] == "Set 2"
    assert parsed["year"] == "" 
    assert parsed["category"] == ""
    assert parsed["preview_image_url"] == ""
    
    assert parsed["inventory"] == [
        {
            "brick_type_id": "",
            "color_id": "",
            "count": "",
            "brick_name": "",
            "preview_image_url": ""
        }
    ]

def test_get_set_and_inventory_no_rows(): #checks if get_set_and_inventory returns correct json string when no rows are returned from the database
    expected_query = """
        SELECT s.id, s.name, COALESCE(s.year::text, ''), s.category, s.preview_image_url, inv.brick_type_id, inv.color_id, inv.count, b.name, b.preview_image_url
        FROM lego_set s 
        LEFT JOIN lego_inventory inv ON s.id=inv.set_id 
        LEFT JOIN lego_brick b ON inv.brick_type_id = b.brick_type_id AND inv.color_id = b.color_id
        WHERE s.id = %s
    """

    fake_rows = [] #no rows returned

    db = MockDB(expected_query, ("3",), fake_rows)
    result = get_set_and_inventory(db, "3")
    parsed = json.loads(result)

    assert parsed["set_id"] == "3" #returns set_id even if no rows are returned, since we initialize it in the result dict.
    assert parsed["name"] == ""
    assert parsed["year"] == "" 
    assert parsed["category"] == ""
    assert parsed["preview_image_url"] == ""
    
    assert parsed["inventory"] == []

def test_get_set_and_inventory_html_escape(): #checks if get_set_and_inventory correctly escapes html special characters to prevent XSS vulnerabilities
    expected_query = """
        SELECT s.id, s.name, COALESCE(s.year::text, ''), s.category, s.preview_image_url, inv.brick_type_id, inv.color_id, inv.count, b.name, b.preview_image_url
        FROM lego_set s 
        LEFT JOIN lego_inventory inv ON s.id=inv.set_id 
        LEFT JOIN lego_brick b ON inv.brick_type_id = b.brick_type_id AND inv.color_id = b.color_id
        WHERE s.id = %s
    """

    fake_rows = [
        (4, "<Set & 4>", "2021", "Category <B>", "url&4", "102", "12", "4", "Brick <C>", "brick_url_c"),
    ]

    db = MockDB(expected_query, ("4",), fake_rows)
    result = get_set_and_inventory(db, "4")
    parsed = json.loads(result)

    assert parsed["set_id"] == "4"
    assert parsed["name"] == "&lt;Set &amp; 4&gt;" #the actual output it should have after escaping
    assert parsed["year"] == "2021"
    assert parsed["category"] == "Category &lt;B&gt;"
    assert parsed["preview_image_url"] == "url&amp;4"
    
    assert parsed["inventory"] == [
        {
            "brick_type_id": "102",
            "color_id": "12",
            "count": "4",
            "brick_name": "Brick &lt;C&gt;",
            "preview_image_url": "brick_url_c"
        }
    ]

def test_get_next_sets_forward():
    expected_query = """
        SELECT id, name, year, category, preview_image_url
        FROM lego_set
        WHERE id > %s
        ORDER BY id
        LIMIT %s
    """

    fake_rows = [
        (11, "Set A", 2001, "City", "a.jpg"),
        (12, "Set B", 2002, "Space", "b.jpg"),
        (13, "Set C", 2003, "Castle", "c.jpg"),
    ]

    db = MockDB(expected_query, (10, 3), fake_rows) #limit is 2 but we fetch 3 to check if has next in function
    result = get_next_sets_forward(db, cursor=10, limit=2)

    assert result == {
        "rows": [
            {
                "id": 11,
                "name": "Set A",
                "year": 2001,
                "category": "City",
                "preview_image_url": "a.jpg"
            },
            {
                "id": 12,
                "name": "Set B",
                "year": 2002,
                "category": "Space",
                "preview_image_url": "b.jpg"
            }
        ],
        "next_cursor": 12,
        "prev_cursor": 11,
        "limit": 2
    }

def test_get_next_sets_forward_order(): #check explicitly that order is correct
    expected_query = """
        SELECT id, name, year, category, preview_image_url
        FROM lego_set
        WHERE id > %s
        ORDER BY id
        LIMIT %s
    """

    fake_rows = [
        (11, "Set A", 2001, "City", "a.jpg"),
        (12, "Set B", 2002, "Space", "b.jpg"),
        (13, "Set C", 2003, "Castle", "c.jpg"),
    ]

    db = MockDB(expected_query, (10, 3), fake_rows)
    result = get_next_sets_forward(db, cursor=10, limit=2)

    ids = [row["id"] for row in result["rows"]]
    assert ids == [11, 12]

def test_get_next_sets_forward_no_next_page():
    expected_query = """
        SELECT id, name, year, category, preview_image_url
        FROM lego_set
        WHERE id > %s
        ORDER BY id
        LIMIT %s
    """

    fake_rows = [
        (11, "Set A", 2001, "City", "a.jpg"),
        (12, "Set B", 2002, "Space", "b.jpg"),
    ]

    db = MockDB(expected_query, (10, 3), fake_rows)
    result = get_next_sets_forward(db, cursor=10, limit=2)

    assert result["next_cursor"] is None
    assert result["prev_cursor"] == 11

def test_get_next_sets_backward():
    expected_query = """
        SELECT id, name, year, category, preview_image_url
        FROM lego_set
        WHERE id < %s
        ORDER BY id DESC
        LIMIT %s
    """

    fake_rows = [
        (12, "Set B", 2002, "Space", "b.jpg"),
        (11, "Set A", 2001, "City", "a.jpg"),
        (10, "Set C", 2003, "Castle", "c.jpg"),
    ]

    db = MockDB(expected_query, (13, 3), fake_rows) #limit is 2 but we fetch 3 to check if has next in function
    result = get_next_sets_backward(db, cursor=13, limit=2)

    assert result == {
        "rows": [
            {
                "id": 11,
                "name": "Set A",
                "year": 2001,
                "category": "City",
                "preview_image_url": "a.jpg"
            },
            {
                "id": 12,
                "name": "Set B",
                "year": 2002,
                "category": "Space",
                "preview_image_url": "b.jpg"
            }
        ],
        "next_cursor": 12,
        "prev_cursor": 11,
        "limit": 2
    }

def test_get_next_sets_backward_order(): #check explicitly that order is correct for backward as well
    expected_query = """
        SELECT id, name, year, category, preview_image_url
        FROM lego_set
        WHERE id < %s
        ORDER BY id DESC
        LIMIT %s
    """

    fake_rows = [ #backwars order since that is result from query
        (19, "Set A", 2001, "City", "a.jpg"),
        (18, "Set B", 2002, "Space", "b.jpg"),
        (17, "Set C", 2003, "Castle", "c.jpg"),
    ]

    db = MockDB(expected_query, (20, 3), fake_rows)
    result = get_next_sets_backward(db, cursor=20, limit=2)

    ids = [row["id"] for row in result["rows"]]
    assert ids == [18, 19] #should be order asceningly

def test_get_next_sets_backward_no_previous_page():
    expected_query = """
        SELECT id, name, year, category, preview_image_url
        FROM lego_set
        WHERE id < %s
        ORDER BY id DESC
        LIMIT %s
    """

    fake_rows = [
        (2, "Set B", 2002, "Space", "b.jpg"),
        (1, "Set A", 2001, "City", "a.jpg"),
    ]

    db = MockDB(expected_query, (3, 3), fake_rows)
    result = get_next_sets_backward(db, cursor=3, limit=2)

    assert [row["id"] for row in result["rows"]] == [1, 2]
    assert result["next_cursor"] == 2
    assert result["prev_cursor"] is None


def test_encode_page_html_defaults_to_utf8(): #checks that default encoding is UTF-8 
    html = "<meta charset='{CHARSET}'><h1>Hei</h1>"

    compressed, used_encoding = encode_page_html(html, None)
    decoded = gzip.decompress(compressed).decode("UTF-8")

    assert used_encoding == "UTF-8"
    assert "UTF-8" in decoded
    assert "{CHARSET}" not in decoded
    assert "<h1>Hei</h1>" in decoded

def test_encode_page_html_invalid_encoding_defaults_to_utf8(): #checks handeling of invalid encoding
    html = "<meta charset='{CHARSET}'>"

    compressed, used_encoding = encode_page_html(html, "latin1")
    decoded = gzip.decompress(compressed).decode("UTF-8")

    assert used_encoding == "UTF-8"
    assert "UTF-8" in decoded

def test_encode_page_html_utf16(): #checks that valid encoding works
    html = "<meta charset='{CHARSET}'><h1>Hei</h1>"

    compressed, used_encoding = encode_page_html(html, "UTF-16")
    decoded = gzip.decompress(compressed).decode("UTF-16")

    assert used_encoding == "UTF-16"
    assert "UTF-16" in decoded
    assert "<h1>Hei</h1>" in decoded

def test_serialize_set_to_binary_data_returns_bytes(): #weak test to check return is bytes and not empty
    result = {
        "set_id": "1",
        "name": "Set 1",
        "year": "2020",
        "category": "City",
        "preview_image_url": "http://example.com/set.jpg",
        "inventory": [
            {
                "brick_type_id": "123",
                "color_id": "10",
                "count": "2",
                "brick_name": "Brick A",
                "preview_image_url": "http://example.com/456.jpg"
            }
        ]
    }

    data = serialize_set_to_binary_data(result)

    assert isinstance(data, bytes)
    assert len(data) > 0

