from src.dashboard.views import device, file_system, memory, network, parallel, process, security

VIEWS = [view.VIEW for view in (process, memory, file_system, security, device, network, parallel)]
