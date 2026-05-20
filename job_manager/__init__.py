"""job_manager — Backend de encolamiento de procesos largos para el agente.

Servicio FastAPI en localhost:8090. Persistencia SQLite. Workers en subprocess.
Emite eventos en formato standard `JOB|<evento>|<id>|<name>|<estado>|<k=v>` a
`logs/jobs/events.log` para que monitor_hub o un Monitor de Claude los capture.
"""
