from src.dashboard.views import device, file_system, memory, network, parallel, process, security
from src.dashboard.views.scenario_builder import VIEW as scenario_builder_view
VIEWS = [view.VIEW for view in (process, memory, file_system, security, device, network, parallel)] + [scenario_builder_view]
