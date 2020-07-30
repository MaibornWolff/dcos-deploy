from ..adapters.dcos import DcosAdapter
from ..auth import get_base_url


def calculate_predefined_variables():
    dcos_adapter = DcosAdapter()
    cluster_info = dcos_adapter.get_cluster_info()
    cluster_state = dcos_adapter.get_cluster_state()
    counts = dcos_adapter.get_node_counts()
    return dict(
        _cluster_version=cluster_info["version"],
        _cluster_variant=cluster_info["variant"],
        _cluster_name=cluster_state["cluster"],
        _cluster_base_url=get_base_url(),
        _num_masters=counts["master"],
        _num_private_agents=counts["agent"], 
        _num_public_agents=counts["public_agent"],
        _num_all_agents=counts["agent"]+counts["public_agent"]
    )
