#!/usr/bin/env python3
"""
Script để test Authentication APIs
Sử dụng: python scripts/test_auth_api.py
"""

import requests
import json
import time
from typing import Dict, Any


class AuthAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token = None
        self.refresh_token = None

    def test_health_check(self) -> bool:
        """Test health check endpoint"""
        print("🔍 Testing health check...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

    def test_register(self, user_data: Dict[str, Any]) -> bool:
        """Test user registration"""
        print("🔍 Testing user registration...")
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/register",
                json=user_data
            )
            
            if response.status_code == 201:
                data = response.json()
                print(f"✅ Registration successful: {data}")
                return True
            else:
                print(f"❌ Registration failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False

    def test_login(self, login_data: Dict[str, Any]) -> bool:
        """Test user login"""
        print("🔍 Testing user login...")
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json=login_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                print(f"✅ Login successful: {data}")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

    def test_get_current_user(self) -> bool:
        """Test get current user info"""
        print("🔍 Testing get current user...")
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = self.session.get(
                f"{self.base_url}/api/v1/auth/me",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Get current user successful: {data}")
                return True
            else:
                print(f"❌ Get current user failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Get current user error: {e}")
            return False

    def test_refresh_token(self) -> bool:
        """Test token refresh"""
        print("🔍 Testing token refresh...")
        if not self.refresh_token:
            print("❌ No refresh token available")
            return False
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json={"refresh_token": self.refresh_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                print(f"✅ Token refresh successful: {data}")
                return True
            else:
                print(f"❌ Token refresh failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Token refresh error: {e}")
            return False

    def test_logout(self) -> bool:
        """Test user logout"""
        print("🔍 Testing user logout...")
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/logout",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Logout successful: {data}")
                return True
            else:
                print(f"❌ Logout failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Logout error: {e}")
            return False

    def test_update_user(self, update_data: Dict[str, Any]) -> bool:
        """Test update user info"""
        print("🔍 Testing update user...")
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = self.session.put(
                f"{self.base_url}/api/v1/auth/me",
                json=update_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Update user successful: {data}")
                return True
            else:
                print(f"❌ Update user failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Update user error: {e}")
            return False

    def run_all_tests(self):
        """Run all authentication tests"""
        print("🚀 Starting Authentication API Tests...")
        print("=" * 50)
        
        # Test data
        user_data = {
            "email": f"test_{int(time.time())}@example.com",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
            "full_name": "Test User",
            "phone": "+1234567890",
            "role": "candidate"
        }
        
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        
        update_data = {
            "full_name": "Updated Test User",
            "phone": "+0987654321"
        }
        
        # Run tests
        tests = [
            ("Health Check", self.test_health_check),
            ("User Registration", lambda: self.test_register(user_data)),
            ("User Login", lambda: self.test_login(login_data)),
            ("Get Current User", self.test_get_current_user),
            ("Update User", lambda: self.test_update_user(update_data)),
            ("Token Refresh", self.test_refresh_token),
            ("User Logout", self.test_logout),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}")
            print("-" * 30)
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ Test error: {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        print("=" * 50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n🎯 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed. Check the logs above.")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Authentication APIs")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Create tester
    tester = AuthAPITester(args.url)
    
    # Run tests
    tester.run_all_tests()


if __name__ == "__main__":
    main()
