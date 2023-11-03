from st_files_connection import FilesConnection


def save_data_gcs(data_path: str, to_path: str, conn: FilesConnection):
    conn.fs.put_file(data_path, to_path)


def get_data_gcs(data_path: str, to_path: str, conn: FilesConnection):
    print(f"Getting file {data_path} from cloud")
    conn.fs.get_file(data_path, to_path)


def load_data_gcs(data_path: str, conn: FilesConnection):
    df = conn.read(data_path, input_format="csv", ttl=60)

    return df
