from modules.shared.http import response


def test_cors_allows_authenticated_delete_requests():
    headers = response(200, {})["headers"]

    assert "DELETE" in headers["Access-Control-Allow-Methods"]
    assert "Authorization" in headers["Access-Control-Allow-Headers"]
