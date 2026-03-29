"""
Tests for the Mergington High School Activities API

Tests cover all endpoints:
- GET / (redirect)
- GET /activities
- POST /activities/{activity_name}/signup
- DELETE /activities/{activity_name}/participants/{email}
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


class TestRootRedirect:
    """Tests for GET / endpoint"""

    def test_root_redirects_to_static_index(self, client):
        """Test that root path redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        activities = response.json()
        
        # Verify it's a dictionary with activities
        assert isinstance(activities, dict)
        assert len(activities) > 0

    def test_get_activities_contains_expected_activities(self, client):
        """Test that all expected activities are present"""
        response = client.get("/activities")
        activities = response.json()
        
        expected_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Basketball Team",
            "Tennis Club",
            "Art Studio",
            "Drama Club",
            "Debate Team",
            "Science Club"
        ]
        
        for activity_name in expected_activities:
            assert activity_name in activities

    def test_activity_has_correct_structure(self, client):
        """Test that each activity has the required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in activities.items():
            for field in required_fields:
                assert field in activity_data, f"Activity {activity_name} missing field {field}"
                
            # Verify types
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)

    def test_participants_are_email_strings(self, client):
        """Test that participants are valid email strings"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            for email in activity_data["participants"]:
                assert isinstance(email, str)
                assert "@" in email, f"Invalid email format: {email}"


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_successful(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert "newstudent@mergington.edu" in result["message"]
        assert "Chess Club" in result["message"]

    def test_signup_adds_participant_to_activity(self, client):
        """Test that signup actually adds the participant to the activity"""
        email = "testuser@mergington.edu"
        
        # Get activities before signup
        response_before = client.get("/activities")
        activities_before = response_before.json()
        participants_before = activities_before["Chess Club"]["participants"]
        
        # Sign up
        client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        
        # Get activities after signup
        response_after = client.get("/activities")
        activities_after = response_after.json()
        participants_after = activities_after["Chess Club"]["participants"]
        
        # Verify participant was added
        assert email in participants_after
        assert email not in participants_before
        assert len(participants_after) == len(participants_before) + 1

    def test_signup_nonexistent_activity_returns_404(self, client):
        """Test that signup for nonexistent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        result = response.json()
        assert "Activity not found" in result["detail"]

    def test_signup_duplicate_email_returns_400(self, client):
        """Test that duplicate signup returns 400 error"""
        email = "michael@mergington.edu"  # Already signed up for Chess Club
        
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 400
        result = response.json()
        assert "already signed up" in result["detail"]

    def test_signup_with_empty_email(self, client):
        """Test that signup with empty email is handled"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": ""}
        )
        # Empty string is technically added, but verify it doesn't crash
        assert response.status_code == 200

    def test_signup_same_person_different_activities(self, client):
        """Test that same person can sign up for different activities"""
        email = "versatile@mergington.edu"
        
        # Sign up for first activity
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Sign up for second activity
        response2 = client.post(
            "/activities/Programming Class/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify both signups were successful
        activities = client.get("/activities").json()
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Programming Class"]["participants"]


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""

    def test_remove_participant_successful(self, client):
        """Test successful removal of a participant"""
        email = "michael@mergington.edu"  # Already in Chess Club
        
        # Verify participant is there
        activities_before = client.get("/activities").json()
        assert email in activities_before["Chess Club"]["participants"]
        
        # Remove participant
        response = client.delete(
            f"/activities/Chess Club/participants/{email}"
        )
        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert email in result["message"]
        
        # Verify participant was removed
        activities_after = client.get("/activities").json()
        assert email not in activities_after["Chess Club"]["participants"]

    def test_remove_nonexistent_activity_returns_404(self, client):
        """Test that removing from nonexistent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent Activity/participants/student@mergington.edu"
        )
        assert response.status_code == 404
        result = response.json()
        assert "Activity not found" in result["detail"]

    def test_remove_nonexistent_participant_returns_404(self, client):
        """Test that removing nonexistent participant returns 404"""
        response = client.delete(
            "/activities/Chess Club/participants/nonexistent@mergington.edu"
        )
        assert response.status_code == 404
        result = response.json()
        assert "Participant not found" in result["detail"]

    def test_remove_participant_decreases_count(self, client):
        """Test that removing a participant decreases participant count"""
        email = "daniel@mergington.edu"  # Already in Chess Club
        
        # Get count before
        activities_before = client.get("/activities").json()
        count_before = len(activities_before["Chess Club"]["participants"])
        
        # Remove participant
        client.delete(f"/activities/Chess Club/participants/{email}")
        
        # Get count after
        activities_after = client.get("/activities").json()
        count_after = len(activities_after["Chess Club"]["participants"])
        
        # Verify count decreased
        assert count_after == count_before - 1

    def test_remove_then_signup_same_person(self, client):
        """Test that person can sign up again after being removed"""
        email = "michael@mergington.edu"
        
        # Remove from Chess Club
        client.delete(f"/activities/Chess Club/participants/{email}")
        
        # Verify removed
        activities = client.get("/activities").json()
        assert email not in activities["Chess Club"]["participants"]
        
        # Sign up again
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify back in activity
        activities = client.get("/activities").json()
        assert email in activities["Chess Club"]["participants"]


class TestIntegration:
    """Integration tests for complete workflows"""

    def test_complete_signup_and_removal_workflow(self, client):
        """Test complete workflow: signup, view, remove"""
        new_email = "integration@mergington.edu"
        activity = "Programming Class"
        
        # Get initial state
        initial = client.get("/activities").json()
        initial_count = len(initial[activity]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup",
            params={"email": new_email}
        )
        assert signup_response.status_code == 200
        
        # Verify added
        after_signup = client.get("/activities").json()
        assert new_email in after_signup[activity]["participants"]
        assert len(after_signup[activity]["participants"]) == initial_count + 1
        
        # Remove
        remove_response = client.delete(
            f"/activities/{activity}/participants/{new_email}"
        )
        assert remove_response.status_code == 200
        
        # Verify removed
        after_removal = client.get("/activities").json()
        assert new_email not in after_removal[activity]["participants"]
        assert len(after_removal[activity]["participants"]) == initial_count

    def test_multiple_signups_and_removals(self, client):
        """Test multiple operations in sequence"""
        activity = "Gym Class"
        emails = [
            "multi1@mergington.edu",
            "multi2@mergington.edu",
            "multi3@mergington.edu"
        ]
        
        # Sign up multiple people
        for email in emails:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all signed up
        activities = client.get("/activities").json()
        for email in emails:
            assert email in activities[activity]["participants"]
        
        # Remove all
        for email in emails:
            response = client.delete(
                f"/activities/{activity}/participants/{email}"
            )
            assert response.status_code == 200
        
        # Verify all removed
        activities = client.get("/activities").json()
        for email in emails:
            assert email not in activities[activity]["participants"]
