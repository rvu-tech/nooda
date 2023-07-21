import json

from os.path import basename
from typing import Optional


def running_in_databricks() -> bool:
    try:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.getOrCreate()
        dbutils = DBUtils(spark)
        return True
    except Exception:
        return False


def notebook_name(spark=None) -> str:
    if spark is None:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.getOrCreate()

    dbutils = DBUtils(spark)

    return basename(
        dbutils.notebook.entry_point.getDbutils()
        .notebook()
        .getContext()
        .notebookPath()
        .get()
    )


def notebook_url(spark=None) -> str:
    if spark is None:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.getOrCreate()

    dbutils = DBUtils(spark)

    workspace_url = spark.conf.get("spark.databricks.workspaceUrl")
    notebook_config = json.loads(
        dbutils.notebook.entry_point.getDbutils().notebook().getContext().toJson()
    )["tags"]

    return f"https://{workspace_url}/?o={notebook_config['orgId']}#notebook/{notebook_config['notebookId']}"


def job_url(spark=None) -> Optional[str]:
    if spark is None:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.getOrCreate()

    dbutils = DBUtils(spark)

    workspace_url = spark.conf.get("spark.databricks.workspaceUrl")
    notebook_config = json.loads(
        dbutils.notebook.entry_point.getDbutils().notebook().getContext().toJson()
    )["tags"]

    if "jobId" in notebook_config and "multitaskParentRunId" in notebook_config:
        return f"https://{workspace_url}/?o={notebook_config['orgId']}#job/{notebook_config['jobId']}/run/{notebook_config['multitaskParentRunId']}"
    else:
        return None


def notebook_path(spark=None) -> str:
    if spark is None:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.getOrCreate()

    dbutils = DBUtils(spark)

    return (
        dbutils.notebook.entry_point.getDbutils()
        .notebook()
        .getContext()
        .notebookPath()
        .get()
    )
