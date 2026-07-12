from ecommerce_dataops.sql_utils import split_sql


def test_split_sql_handles_comments_and_semicolons_in_strings():
    text = """
    -- leading comment;
    SELECT 'a; b' AS value;
    /* block ; comment */
    SELECT `semi;colon`, "quoted;identifier" FROM sample;
    """
    assert split_sql(text) == [
        "SELECT 'a; b' AS value",
        'SELECT `semi;colon`, "quoted;identifier" FROM sample',
    ]


def test_split_sql_keeps_escaped_single_quotes():
    assert split_sql("SELECT 'it''s; fine'; SELECT 2;") == ["SELECT 'it''s; fine'", "SELECT 2"]

