"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy()
        }
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, activity in original_activities.items():
        if name in activities:
            activities[name]["participants"] = activity["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for getting activities"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Chess Club" in data
        assert "Soccer Team" in data
    
    def test_activity_structure(self, client):
        """Test that activities have correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for name, activity in data.items():
            assert "description" in activity
            assert "schedule" in activity
            assert "max_participants" in activity
            assert "participants" in activity
            assert isinstance(activity["participants"], list)
            assert isinstance(activity["max_participants"], int)


class TestSignup:
    """Tests for signing up to activities"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        email = "test@mergington.edu"
        activity_name = "Chess Club"
        
        # Remove email if it exists
        if email in activities[activity_name]["participants"]:
            activities[activity_name]["participants"].remove(email)
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify email was added
        assert email in activities[activity_name]["participants"]
    
    def test_signup_duplicate_fails(self, client):
        """Test that signing up twice fails"""
        email = "duplicate@mergington.edu"
        activity_name = "Drama Club"
        
        # First signup
        client.post(f"/activities/{activity_name}/signup?email={email}")
        
        # Second signup should fail
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_invalid_activity(self, client):
        """Test signup for non-existent activity"""
        email = "test@mergington.edu"
        activity_name = "Nonexistent Club"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestUnregister:
    """Tests for unregistering from activities"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        email = "unregister@mergington.edu"
        activity_name = "Swimming Club"
        
        # First signup
        client.post(f"/activities/{activity_name}/signup?email={email}")
        assert email in activities[activity_name]["participants"]
        
        # Then unregister
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify email was removed
        assert email not in activities[activity_name]["participants"]
    
    def test_unregister_not_signed_up(self, client):
        """Test unregistering when not signed up fails"""
        email = "notsignedup@mergington.edu"
        activity_name = "Art Studio"
        
        # Ensure not signed up
        if email in activities[activity_name]["participants"]:
            activities[activity_name]["participants"].remove(email)
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not signed up" in data["detail"].lower()
    
    def test_unregister_invalid_activity(self, client):
        """Test unregister from non-existent activity"""
        email = "test@mergington.edu"
        activity_name = "Nonexistent Club"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestEndToEnd:
    """End-to-end tests"""
    
    def test_complete_signup_and_unregister_flow(self, client):
        """Test complete flow: signup and then unregister"""
        email = "endtoend@mergington.edu"
        activity_name = "Debate Team"
        
        # Get initial activities
        response = client.get("/activities")
        initial_participants = response.json()[activity_name]["participants"].copy()
        
        # Signup
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify participant was added
        response = client.get("/activities")
        current_participants = response.json()[activity_name]["participants"]
        assert email in current_participants
        assert len(current_participants) == len(initial_participants) + 1
        
        # Unregister
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify participant was removed
        response = client.get("/activities")
        final_participants = response.json()[activity_name]["participants"]
        assert email not in final_participants
        assert len(final_participants) == len(initial_participants)
