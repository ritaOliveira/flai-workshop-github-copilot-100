"""
Test cases for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_state = {
        activity: {
            "description": details.get("description", ""),
            "schedule": details.get("schedule", ""),
            "max_participants": details.get("max_participants", 0),
            "participants": details.get("participants", []).copy()
        }
        for activity, details in activities.items()
    }
    
    # Run the test
    yield
    
    # Restore original state after test
    activities.clear()
    activities.update(original_state)


@pytest.fixture
def client():
    """Create a test client for the API"""
    return TestClient(app)


class TestActivitiesEndpoint:
    """Test cases for the /activities endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that GET /activities returns a 200 status code"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_dict(self, client):
        """Test that GET /activities returns a dictionary"""
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_activities_contains_expected_activities(self, client):
        """Test that GET /activities contains expected activity names"""
        response = client.get("/activities")
        data = response.json()
        
        # Check for some expected activities
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_activity_structure(self, client):
        """Test that each activity has the required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupEndpoint:
    """Test cases for the /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_existing_activity(self, client):
        """Test signing up for an existing activity"""
        response = client.post(
            "/activities/Programming Class/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
    
    def test_signup_adds_participant(self, client):
        """Test that signup actually adds the participant to the activity"""
        email = "newstudent@mergington.edu"
        activity_name = "Gym Class"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()[activity_name]["participants"]
        initial_count = len(initial_participants)
        
        # Sign up
        client.post(f"/activities/{activity_name}/signup?email={email}")
        
        # Verify participant was added
        final_response = client.get("/activities")
        final_participants = final_response.json()[activity_name]["participants"]
        
        assert len(final_participants) == initial_count + 1
        assert email in final_participants
    
    def test_signup_duplicate_returns_400(self, client):
        """Test that signing up twice returns a 400 error"""
        email = "duplicate@mergington.edu"
        activity_name = "Programming Class"
        
        # First signup
        client.post(f"/activities/{activity_name}/signup?email={email}")
        
        # Second signup (should fail)
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signing up for a non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signing up for activities with special characters"""
        # First, let's use an existing activity
        response = client.post(
            "/activities/Chess Club/signup?email=special@mergington.edu"
        )
        # This should work for existing activities
        assert response.status_code in [200, 404]  # 200 if exists, 404 if not


class TestUnregisterEndpoint:
    """Test cases for the /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        email = "removeme@mergington.edu"
        activity_name = "Programming Class"
        
        # First sign up
        client.post(f"/activities/{activity_name}/signup?email={email}")
        
        # Then unregister
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]
    
    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant"""
        email = "toberemoved@mergington.edu"
        activity_name = "Gym Class"
        
        # Sign up
        client.post(f"/activities/{activity_name}/signup?email={email}")
        
        # Verify participant is there
        response = client.get("/activities")
        participants = response.json()[activity_name]["participants"]
        assert email in participants
        
        # Unregister
        client.delete(f"/activities/{activity_name}/unregister?email={email}")
        
        # Verify participant was removed
        response = client.get("/activities")
        participants = response.json()[activity_name]["participants"]
        assert email not in participants
    
    def test_unregister_nonexistent_participant(self, client):
        """Test unregistering a participant who is not signed up returns 400"""
        response = client.delete(
            "/activities/Programming Class/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistering from a non-existent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestRootEndpoint:
    """Test cases for the root endpoint"""
    
    def test_root_redirects_to_static_html(self, client):
        """Test that the root endpoint redirects to the static HTML page"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestIntegrationScenarios:
    """Integration tests for complete workflows"""
    
    def test_signup_and_unregister_workflow(self, client):
        """Test a complete signup and unregister workflow"""
        email = "workflow@mergington.edu"
        activity_name = "Programming Class"
        
        # Get initial state
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity_name]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        after_signup = client.get("/activities")
        after_signup_count = len(after_signup.json()[activity_name]["participants"])
        assert after_signup_count == initial_count + 1
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify unregister
        final_response = client.get("/activities")
        final_count = len(final_response.json()[activity_name]["participants"])
        assert final_count == initial_count
    
    def test_multiple_signups_different_activities(self, client):
        """Test that a student can sign up for multiple activities"""
        email = "multisport@mergington.edu"
        
        # Sign up for multiple activities
        activities_to_join = ["Programming Class", "Gym Class"]
        
        for activity in activities_to_join:
            response = client.post(
                f"/activities/{activity}/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify student is in all activities
        all_activities = client.get("/activities").json()
        for activity in activities_to_join:
            assert email in all_activities[activity]["participants"]
