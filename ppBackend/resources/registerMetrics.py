import mlflow

def register(experiment_id:str, metrics_dict:dict):
    """
    Registers the provided metrics to the specified experiment in the MLflow tracking server.

    Args:
        experiment_id (str): The ID of the experiment to which the metrics will be registered.
        metrics_dict (dict): A dictionary containing metric names as keys and their corresponding values.

    Returns:
        None
    """

    # Set the experiment context
    mlflow.set_experiment(experiment_id)

    # Start a new run within the experiment
    with mlflow.start_run():
        # Log each metric from the provided dictionary
        for metric_name, metric_value in metrics_dict.items():
            mlflow.log_metric(metric_name, metric_value)