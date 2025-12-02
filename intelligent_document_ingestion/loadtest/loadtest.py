from locust import HttpUser, task, between
import requests, time, uuid, os

USERNAME = "admin"
PASSWORD = "admin@123"
FILE_PATH = "testfile.pdf"

class IdoUser(HttpUser):
    wait_time = between(2, 4)

    def on_start(self):
        # Login once per simulated user
        res = self.client.post(
            "/auth/login",
            data={"username": USERNAME, "password": PASSWORD}
        )
        data = res.json()
        self.token = data["accessToken"]
        self.user_id = data["userId"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
            }
            

    @task
    def full_file_flow(self):
        file_bytes = open(FILE_PATH, "rb").read()
        payload = {
            "userId": self.user_id,
            "fileName": f"test-{uuid.uuid4()}.pdf",
            "fileSize": len(file_bytes),
            "fileType": "application/pdf",
        }

        # step 1 → get presigned URL
        res = self.client.post(
            "/api/v1/uploads/request",
            json=payload,
            headers=self.headers
        )
        print(f"Received Response: {res}")
        
        # Check for successful response
        if res.status_code != 200:
            print(f"Failed to request upload: {res.status_code} {res.text}")
            self.environment.runner.quit()
        else:
            print(f"Upload request successful: test-{uuid.uuid4()}.pdf")
            print(f"Response Content: {res.json()}")
            
        upload = res.json()
        file_id = upload["fileId"]
        upload_url = upload["uploadUrl"]

        # step 2 → PUT to S3
        put_res = requests.put(upload_url, data=file_bytes)
        assert put_res.status_code in [200, 204]

        # step 3 → notify backend
        self.client.post(
            "/api/v1/uploads/complete",
            json={"fileId": file_id},
            headers=self.headers
        )

        # step 4 → poll status with backoff (exactly like UI)
        poll_interval = 2
        while True:
            time.sleep(poll_interval)
            st = self.client.get(
                f"/api/v1/uploads/{file_id}/status",
                headers=self.headers
            )
            print(f"Status Poll Response: {st.status_code} {st.text}")
            if st.status_code != 200:
                print("STATUS ERROR:", st.status_code, st.text)
                self.environment.runner.quit()
                
            status = st.json()["status"]

            if status in ["completed", "failed"]:
                break

            if poll_interval < 8:
                poll_interval += 1


#locust -f loadtest.py --host http://43.205.235.186:8000 --users 10 --spawn-rate 10 --run-time 10 --stop-timeout 30 --csv loadtest --html loadtest.html