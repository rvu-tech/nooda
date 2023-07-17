import json


def running_in_databricks() -> bool:
    try:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.getOrCreate()
        dbutils = DBUtils(spark)
        return True
    except Exception:
        return False


def notebook_url(dbutils=None) -> str:
    if dbutils is None:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.getOrCreate()
        dbutils = DBUtils(spark)

    notebook_config = json.loads(
        dbutils.notebook.entry_point.getDbutils().notebook().getContext().toJson()
    )["tags"]

    return f"https://{notebook_config['browserHostName']}/?o={notebook_config['orgId']}#{notebook_config['browserHash']}"


def notebook_path(dbutils=None) -> str:
    if dbutils is None:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.getOrCreate()
        dbutils = DBUtils(spark)

    context = json.loads(
        dbutils.notebook.entry_point.getDbutils().notebook().getContext().toJson()
    )

    return context["extraContext"]["notebook_path"]
