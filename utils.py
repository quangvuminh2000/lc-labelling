from st_files_connection import FilesConnection

from time import time
from datetime import datetime


def save_data_gcs(data_path: str, to_path: str, conn: FilesConnection):
    start_time = time()
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.fs.put_file(data_path, to_path)
    print(f"{today_str} : Saving data {data_path} to cloud : {time()-start_time:2f}s")


def get_data_gcs(data_path: str, to_path: str, conn: FilesConnection):
    start_time = time()
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.fs.get_file(data_path, to_path)
    print(
        f"{today_str} : Getting file {data_path} from cloud : {time()-start_time:2f}s"
    )


def load_data_gcs(data_path: str, conn: FilesConnection):
    print(f"Loading static data {data_path} from cloud")
    df = conn.read(data_path, input_format="csv", ttl=60)
    return df
