def compose(hosts: list[str]):
    return {
        "services": {
            "web": {
                "image": "nginx:latest",
                "ports": ["80:80"],
                "environment": {
                    "HOSTS": ",".join(hosts),
                },
            }
        }
    }
