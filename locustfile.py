from locust import HttpUser, task, between

class PowerGridUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def test_forecast(self):
        self.client.get("/forecast")

    @task(2)
    def test_health(self):
        self.client.get("/health")
        
    @task(1)
    def test_alerts(self):
        self.client.get("/alerts")
