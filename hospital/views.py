import os
import datetime

import xlrd
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from hospital.models import Patient, Pstatus, Hospital

# 输出嵌套格式举例：LOCATION = {'吉林省': {'长春市': ['南关区', '朝阳区', '二道区', '绿园区']}}
STRING_LOCATION = {}  # 解析得到xml文件中的名字（key为单个字符串）
CODED_LOCATION = {}  # 用于记录确切的地理编码（key为元组）
# 0->治愈 1->无症状 2->轻症 3->重症 4->死亡

HOSPITAL_USERNAME = ""  # 先假设一个全局的用户
HOSPITAL_PASSWORD = ""
STATUS = {"治愈": 0, "无症状": 1, "轻症": 2, "重症": 3, "死亡": 4}

error_data = {}  # 记录错误数据
ERROR_INFO = {"ERROR-101": "病案号过长",
              "ERROR-102": "电话号过长",
              "ERROR-103": "日期出现错误，超前时间",
              "ERROR-201": "系统错误：patient表中有多条相同的病人记录",
              "ERROR-202": "此次上传更新数据中与已有病人状态冲突，请检查病人ID和状态",
              "ERROR-203": "此次上传更新数据中有已死亡病人的状态变化，请检查病人ID和装态"
              }
DATA_FIELD = {"病案号": 1, "电话": 2, "用户名": 3, "状态": 4, "日期": 5}
field_indexes = []  # 存储excel文件中的表头和数据库字段的对应关系


class Summary:
    healthy = 0
    behavior_less_sum = 0
    light_sum = 0
    severe_sum = 0
    dead = 0


# 使用相应的url来调用相应的函数
def index(request):
    return render(request, 'index.html')


def hospital_login(request):
    return render(request, 'login.html')


# 医院用户身份认证入口
def hospital_confirmed(request):
    a = request.GET
    username = a.get('username')
    password = a.get('password')
    identified = hospital_identify(username, password)
    if identified == 1:  # 验证成功则渲染upload页面
        render(request, 'upload.html')
        return HttpResponseRedirect('/upload')
    elif identified == 0:
        render(request, 'hospital_login.html')
        return HttpResponseRedirect('/hospital_login')  # 登录信息验证失败，重定向回到login页面，不发生改变
    else:
        return render(request, 'fail.html')  # 验证失败就渲染失败页面


# 医院用户身份认证DAO
def hospital_identify(username, password_):
    print(username, password_)
    result = Hospital.objects.filter(username=username)  # 找出该用户的记录
    if result.exists():  # 有这个用户
        hospital = result.first()
        password = hospital.passwd
        if password == password_:
            global HOSPITAL_USERNAME
            HOSPITAL_USERNAME = username
            global HOSPITAL_PASSWORD
            HOSPITAL_PASSWORD = password
            print("验证成功，用户已授权")
            return 1
        else:
            print("密码错误")
            return 0
    else:
        print("医院用户名错误")
        return -1


# 疫情上报界面的处理逻辑
def upload(request):
    status_queryset = {}  # 记录不同状态人数的统计数据
    status_queryset.update({"healthy": len(Patient.objects.filter(status=0))})
    status_queryset.update({"no_behavior": len(Patient.objects.filter(status=1))})
    status_queryset.update({"light": len(Patient.objects.filter(status=2))})
    status_queryset.update({"severe": len(Patient.objects.filter(status=3))})
    status_queryset.update({"dead": len(Patient.objects.filter(status=4))})

    print(status_queryset)

    if request.method == "POST":  # 请求方法为POST时，进行处理
        files = request.FILES.get("myfile", None)  # 获取上传的文件，如果没有文件，则默认为None
        if not files:
            return HttpResponse("no files for upload!")
        # 上传到static中的upload文件夹
        destination = open(os.path.join("./static/upload", files.name), 'wb+')  # 打开特定的文件进行二进制的写操作
        # 如果文件大于2.5MB使用chunks分块
        for chunk in files.chunks():
            destination.write(chunk)
        destination.close()

        filename = files.name
        parse_file(os.path.join("./static/upload", filename))
        render(request, 'upload.html', {'statuses': status_queryset})
        return HttpResponseRedirect('/upload')
    else:
        return render(request, 'upload.html', {'statuses': status_queryset, 'error_info': error_data})


def parse_file(filepath):
    # 读取上传的excel文件
    excel_uploaded = xlrd.open_workbook(filepath)
    sheets_name = excel_uploaded.sheet_names()
    sheet_len = len(sheets_name)  # 获得个数
    if sheet_len == 0:  # 没有表格返回false
        return False
    else:
        sheet = excel_uploaded.sheets()[0]  # 只读取第一张表格
        row_num = sheet.nrows  # 获取当前表格的行数
        col_num = sheet.ncols  # 获取当前表格的列数

        # 以下的错误情况是不能继续读取的
        if col_num != 5:
            print("字段个数不等")
            return -5

        data_field_in_file = sheet.row_values(0)  # 获取第一行的内容（即excel的表头）

        for value in data_field_in_file:
            if value not in DATA_FIELD.keys():
                print("字段名称不符")
                return -4
            else:
                field_indexes.append(DATA_FIELD[value])

        save_patient(sheet, row_num, col_num)
        return True


# 根据读取到的数据，创建对象并保存到数据库中
def save_patient(sheet, row_num, col_num):
    # 需要用到的临时变量,当前登录医院用户对应的医院id
    hospital_id = Hospital.objects.filter(username=HOSPITAL_USERNAME, passwd=HOSPITAL_PASSWORD)[0].h_id
    print(hospital_id)  # 1
    patient_no = ""
    patient_tel = ""
    patient_status = 0
    today = datetime.date.today()  # 先初始化日期为今天
    patient_day = datetime.date.today()
    is_field_valid = True

    for i in range(1, row_num):
        print("现在在解析第", i, "条数据")
        is_field_valid = True
        row = sheet.row_values(i)  # 获取每一行的数据
        for j in range(0, col_num):
            # 根据当前的列数找到此列对应的字段在数据库终的字段的下标
            field_index = field_indexes[j]
            if field_index == 1:  # 病案号
                if len(str(row[j])) <= 64:
                    patient_no = str(int(row[j]))  # float to string
                else:
                    create_error_info("ERROR-101", str(int(row[j])))
                    is_field_valid = False
                    break  # 不再对当前这条数据操作，直接读取下一条数据
            elif field_index == 2:  # 电话，满足长度小于20的字符串
                if len(str(row[j])) <= 20:
                    patient_tel = str(int(row[j]))  # float to string
                else:
                    create_error_info("ERROR-102", str(int(row[j])))
                    is_field_valid = False
                    break  # 不再对当前这条数据操作，直接读取下一条数据
            elif field_index == 4:  # 状态
                patient_status = int(row[j])
            elif field_index == 5:  # 日期
                dt = xlrd.xldate.xldate_as_datetime(row[j], 0)  # 0和1用于区分是以1900作为标准还是以1904作为标准
                patient_day = datetime.date(dt.year, dt.month, dt.day)  # 将excel表格中的日期数据转换为python中的日期格式
                print(patient_day)
                if today < patient_day:  # 录入的日期在今天之后
                    create_error_info("ERROR-103", patient_day)
                    is_field_valid = False
                    break  # 不再对当前这条数据操作，直接读取下一条数据

        if is_field_valid:  # 如果数据是正确的，才会进行这条数据的存储
            # 当一行的数据错误异常处理完成之后，将要进行存储操作
            # 找到该病案号、电话号的病人
            patient_list = Patient.objects.filter(no=patient_no, tel=patient_tel)
            # 之前不存在这样的病人，直接插入病人表，同时修改病人状态表，也不需要重新找最新的状态
            if len(patient_list) == 0:
                # 创建一个新的病人，更新病人表中的记录，插入数据
                patient_new = Patient(h_id=hospital_id, no=patient_no, tel=patient_tel, status=patient_status)
                patient_new.save()

                # 获取该病人的id（auto_incremented），插入状态表
                patient_id = Patient.objects.filter(no=patient_no, tel=patient_tel)[0].p_id
                print("新建一个病人", patient_id, patient_status)

                # 更新状态表，新增记录
                pstatus_new = Pstatus(p_id=patient_id, status=patient_status, day=patient_day)
                pstatus_new.save()
                # 之前存在这样的病人（只有一条）
            elif len(patient_list) == 1:
                patient_id = patient_list[0].p_id
                print("此时单元格的病人id", patient_id)
                print("此时病人的状态", patient_status)

                # 先判断是否为已经死亡的病人
                death_record = Pstatus.objects.filter(p_id=patient_id, status=STATUS["死亡"])  # 找到存在死亡状态的病人记录
                # 已经宣判死亡的人不可再进行状态更新
                if len(death_record) == 1:
                    error_data_unit = [patient_id, patient_no, patient_tel, patient_status, patient_day]
                    create_error_info("ERROR-203", error_data_unit)
                    continue

                # 再查找是否与状态表中原来记录的重复（一个病人不能有两条相同状态的记录）
                same_record = Pstatus.objects.filter(p_id=patient_id, status=patient_status)  # 找到跟当前需要存储的病人id和状态相同的记录
                if len(same_record) == 0:  # 不会出现冲突的情况
                    # 在新增病人状态的时候，需要修改病人信息表中的状态为最新
                    latest_record_date = Pstatus.objects.filter(p_id=patient_id).order_by("-day")[0].day  # 因为还没有存储到？
                    print("之前最新的日期", latest_record_date, "现在这条数据的日期", patient_day)
                    if latest_record_date < patient_day:  # 如果今天的日期比当前数据库中的最晚记录日期要晚
                        p_former = Patient.objects.get(p_id=patient_id)
                        p_former.status = patient_status  # 更新病人状态为最新数据
                        p_former.save()
                    # 新增病人的状态记录
                    pstatus_new = Pstatus(p_id=patient_id, status=patient_status, day=patient_day)
                    pstatus_new.save()
                else:
                    # 其他情况即已经存在相同的病人状态记录，则不进行更新
                    error_data_unit = [patient_id, patient_no, patient_tel, patient_status, patient_day]
                    create_error_info("ERROR-202", error_data_unit)
                    continue  # 不进行插入操作，记录数据的错误，继续开始下一行的读取
            else:
                error_data_unit = [patient_no, patient_tel, patient_status, patient_day]
                create_error_info("ERROR-201", error_data_unit)
                continue  # 停止这行的记录,继续开始下一行
        else:
            continue  # 不做其他操作继续外层循环

    print(error_data)
    return 1


def create_error_info(error_code, varied_para):
    if error_code not in error_data:
        error_data[error_code] = (ERROR_INFO[error_code], varied_para)
    else:
        if isinstance(error_data[error_code], list):
            error_data[error_code].append((ERROR_INFO[error_code], varied_para))
        else:  # tuple形式
            tuple_list = [error_data[error_code], (ERROR_INFO[error_code], varied_para)]
            error_data[error_code] = tuple_list


# def parse_error_data():
#     for value in error_data.values():
#         if isinstance(value, list):
#             for tup in value:
#                 if isinstance(tup, tuple):


# 测试部分，会把病案号、电话号码、状态和日期存成float，str

# 根据当前登录状态的医院用户，识别出h_id，默认一个病人只属于一家医院

# 按行读取，获取当前行的病人，若各项数据中有不正确的：对于日期来说，不可以填写当前日期之前的，
# 则将数据填到错误数据列表中
# 可以填用户名但是不存储到数据库

# 若数据格式都正确，判断是否已经存在该病人的记录
# 若原来的patient表中不存在该病人的记录，则创建一个新的病人，填写ta的病案号、电话号码
# 若已经存在记录，查找patient找到该病案号和电话对应的p_id
# 从pStatus表中查找最新的状态日期，对比当前的日期是否错误（即在状态表前面），状态变化是否错误，比如
# 4不可能转到其他的状态（死亡），其他的话状态之间可以互转
# 如果正确，则向状态表中添加一条记录
# 如果不正确，记录到错误列表中

# 仍然存在的错误有：double类型的数据导致在patient中重复插入数据（已经解决，因为直接将float转换为str，而是应该先转为int再转str）、以及status全都变成0(是因为下标的问题，已解决)
# 即使数据已经存在，也要查看是否重复，主要判断这个id的病人的day是否重复，一个病人一天可以存在不同的状态，但是病人不能存在相同的状态数据，所以需要过滤


# 数据格式错误返回0，正确返回1
# 限制上传的数据为病案号、手机号、用户名（可空）、日期（从字段转化为日期格式）、状态（int）


def choose_province(request):
    province = list(STRING_LOCATION.keys())
    return JsonResponse(province, safe=False)


def choose_city(request):
    province = request.GET.get('p')
    cities = list(STRING_LOCATION[province].keys())
    return JsonResponse(cities, safe=False)


def choose_district(request):
    province = request.GET.get('p')
    city = request.GET.get('c')
    districts = STRING_LOCATION[province][city]
    return JsonResponse(districts, safe=False)


# 测试通过省市区查找当前的编码，打印函数
def print_specified_dict(coded_location):
    if isinstance(coded_location, dict):
        for p, c_dict in coded_location.items():
            print("(", p[0], ",", p[1], ")\n")
            if isinstance(c_dict, dict):
                for c, d_dict in c_dict.items():
                    print("\t(", c[0], ",", c[1], ")\n")
                    if isinstance(d_dict, dict):
                        for d, code in d_dict.items():
                            print("\t\t", d, ":", code, "\n")  # 打印key和value


# 根据省市区的名字查找编码，是最终存储到数据库的内容
def search_code_by_name(coded_location, province, city, district):
    code_list = []  # 用一个list把编码传回去
    for p, c_dict in coded_location.items():
        if province == p[0]:
            code_list.append(p[1])
            for c, d_dict in c_dict.items():
                if city == c[0]:
                    code_list.append(c[1])
                    for d, code in d_dict.items():
                        if district == d:
                            code_list.append(code)
    return code_list


# 从xml文件读取省市区的三级级联数据存储到字典中
def get_data(filename):
    try:
        import xml.etree.cElementTree as ET
    except ImportError:
        import xml.etree.ElementTree as ET

    tree = ET.parse(filename)
    root = tree.getroot()

    temp_province_dict = {}
    temp_city_dict = {}
    temp_district_list = []

    # 带有地理位置编码的部分临时变量
    temp_province_dict_specified = {}
    temp_city_dict_specified = {}
    temp_district_dict = {}

    for province in root.iter("p"):
        for city in province.iter("c"):
            for district in city.iter("d"):
                if district.text == city.find("cn").text and (len(city.findall("d")) != 1):
                    continue  # 不添加名字与区相同的市
                temp_district_list.append(district.text)
                temp_district_dict.update({district.text: district.get("d_id")})
            temp_city_dict.update({city.find("cn").text: temp_district_list})
            temp_city_dict_specified.update({(city.find("cn").text, city.get("c_id")): temp_district_dict})
            temp_district_list = []
            temp_district_dict = {}
        temp_province_dict.update({province.find("pn").text: temp_city_dict})
        temp_province_dict_specified.update(
            {(province.find("pn").text, province.get("p_id")): temp_city_dict_specified})
        temp_city_dict = {}
        temp_city_dict_specified = {}
    STRING_LOCATION.update(temp_province_dict)
    CODED_LOCATION.update(temp_province_dict_specified)
