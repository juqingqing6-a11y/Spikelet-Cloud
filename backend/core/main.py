from core import process, predict


def c_main(path, model, ext):
    image_data = process.pre_process(path)
    image_info, image_number = predict.predict(image_data, model, ext)  # ext = jpg

    return image_data[1] + '.' + ext, image_info, image_number


def c_main5(path, model, ext):
    image_data = process.pre_process(path)
    print(image_data)
    image_info, image_number = predict.predict5(image_data, model, ext)  # ext = jpg

    return image_data[1] + '.' + ext, image_info, image_number


def c_main7(path, model, ext):
    image_data = process.pre_process(path)
    image_info, image_number = predict.predict7(image_data, model, ext)  # ext = jpg
    print(image_info, image_number)
    return image_data[1] + '.' + ext, image_info, image_number


def c_main77(path, model, ext):
    image_data = process.pre_process(path)
    image_info, image_number = predict.predict77(image_data, model, ext)  # ext = jpg
    return image_data[1] + '.' + ext, image_info, image_number


if __name__ == '__main__':
    pass
