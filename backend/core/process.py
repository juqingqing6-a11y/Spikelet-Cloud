import os


def pre_process(data_path):
    file_name = os.path.split(data_path)[1].split('.')[0]
    print(file_name)
    return data_path, file_name


