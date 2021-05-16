from locust import HttpUser, task, between

class PostingReadTest(HttpUser):
    wait_time = between(1, 2)

    @task
    def my_task(self):
        self.client.get("/posting")