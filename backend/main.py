from typing import Any, Dict, List, Optional, Union
import hashlib
import secrets

import galois
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# 这个素数 p 固定为教学版系统使用的有限域模数。
FIELD_PRIME = 2305843009213693951

# 这个有限域对象表示真正参与密码学运算的 GF(p)。
FIELD = galois.GF(FIELD_PRIME)

# 这个常量控制内存里最多保留多少轮最近的分发记录。
MAX_ISSUED_SESSIONS = 20

# 这个列表只在当前进程内暂存最近分发过的份额信息，服务重启后会清空。
ISSUED_SESSIONS: List[Dict[str, Any]] = []

print("系统启动：教学版可追踪秘密共享后端正在初始化。")
print(f"系统启动：当前有限域素数 p = {FIELD_PRIME}")
print("系统启动：大整数接口字段统一按十进制字符串传输。")


# 这个类型表示前端既可以传字符串，也可以直接传普通整数。
BigIntegerInput = Union[int, str]


# 这个模型表示最基础的份额输入结构。
class BasicShareInput(BaseModel):
    participant_id: int
    x: BigIntegerInput
    y: BigIntegerInput


# 这个模型表示秘密分发接口的请求体。
class ShareRequest(BaseModel):
    secret: BigIntegerInput
    share_count: int
    threshold: int


# 这个模型表示返回给前端的单个份额对象。
class ShareItem(BaseModel):
    participant_id: int
    x: str
    y: str
    trace_hash: str


# 这个模型表示追踪密钥中的单条记录。
class TraceKeyItem(BaseModel):
    participant_id: int
    trace_hash: str


# 这个模型表示验证密钥中的单个参与者信息。
class VerifyParticipantItem(BaseModel):
    participant_id: int
    trace_hash: str


# 这个模型表示验证密钥整体结构。
class VerifyKey(BaseModel):
    hash_algorithm: str
    participants: List[VerifyParticipantItem]


# 这个模型表示秘密分发接口的响应体。
class ShareResponse(BaseModel):
    field_prime: str
    secret: str
    share_count: int
    threshold: int
    shares: List[ShareItem]
    trace_key: List[TraceKeyItem]
    verify_key: VerifyKey


# 这个模型表示秘密重构接口的请求体。
class ReconstructRequest(BaseModel):
    shares: List[BasicShareInput]


# 这个模型表示秘密重构接口的响应体。
class ReconstructResponse(BaseModel):
    recovered_secret: str


# 这个模型表示单个泄露输出对象。
class LeakedOutputInput(BaseModel):
    leaked_y: BigIntegerInput


# 这个模型表示叛徒追踪接口的请求体。
class TraceRequest(BaseModel):
    reference_shares: List[BasicShareInput]
    leaked_outputs: List[LeakedOutputInput]
    trace_key: List[TraceKeyItem]


# 这个模型表示单条追踪证据。
class EvidenceItem(BaseModel):
    leaked_y: str
    candidate_x_values: List[str]
    matched_participant_ids: List[int]
    proof_x: Optional[str]


# 这个模型表示叛徒追踪接口的响应体。
class TraceResponse(BaseModel):
    trace_result: str
    traitor_id: Optional[int]
    evidence: List[EvidenceItem]


# 这个模型表示验证接口的请求体。
class VerifyRequest(BaseModel):
    verify_key: VerifyKey
    suspect_participant_id: int
    proof_x: BigIntegerInput


# 这个模型表示验证接口的响应体。
class VerifyResponse(BaseModel):
    verified: bool
    expected_hash: str
    provided_hash: str
    message: str


# 这个 FastAPI 应用对象就是后端服务入口。
app = FastAPI(
    title="基于 Shamir 门限的可追踪秘密共享系统",
    description="教学版：Shamir + Hash(x) + 完美黑盒追踪",
    version="1.0.0",
)


# 这个跨域配置允许本地前端开发服务器直接访问后端。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 这个函数负责把原始输入安全解析成 Python 普通整数。
def parse_big_integer(raw_value: BigIntegerInput, field_name: str) -> int:
    print(f"准备解析字段 {field_name}，原始值是：{raw_value}")

    if isinstance(raw_value, bool):
        raise HTTPException(status_code=400, detail=f"{field_name} 不能是布尔值。")

    if isinstance(raw_value, int):
        print(f"字段 {field_name} 已经是普通整数：{raw_value}")
        return raw_value

    if isinstance(raw_value, str):
        cleaned_text = raw_value.strip()
        if cleaned_text == "":
            raise HTTPException(status_code=400, detail=f"{field_name} 不能为空。")

        try:
            parsed_value = int(cleaned_text)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=f"{field_name} 不是合法的十进制整数。") from error

        print(f"字段 {field_name} 解析完成，得到整数值：{parsed_value}")
        return parsed_value

    raise HTTPException(status_code=400, detail=f"{field_name} 的类型不正确。")


# 这个函数负责把普通整数放入有限域 GF(p)。
def to_field_element(raw_int: int, field_name: str):
    print(f"准备把字段 {field_name} 放入有限域 GF(p)，当前数值是：{raw_int}")

    if raw_int < 0 or raw_int >= FIELD_PRIME:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} 必须满足 0 <= {field_name} < p，当前 p = {FIELD_PRIME}。",
        )

    field_value = FIELD(raw_int)
    print(f"字段 {field_name} 已成功转换成有限域元素。")
    return field_value


# 这个函数负责把有限域元素转成普通十进制字符串。
def serialize_field_value(field_value) -> str:
    ordinary_int = int(field_value)
    serialized_text = str(ordinary_int)
    return serialized_text


# 这个函数负责计算 Hash(x)。
def hash_x_value(x_value: int) -> str:
    print(f"准备计算追踪标签 Hash(x)，当前 x = {x_value}")
    hash_text = hashlib.sha256(str(x_value).encode("utf-8")).hexdigest()
    print(f"Hash(x) 计算完成，得到哈希值：{hash_text}")
    return hash_text


# 这个函数负责删除多项式高位多余的 0 系数。
def trim_polynomial_coefficients(coefficients):
    print("准备整理多项式系数，移除高位多余的 0。")

    while len(coefficients) > 1 and coefficients[-1] == FIELD(0):
        coefficients.pop()

    print(f"整理完成，当前多项式阶数是：{len(coefficients) - 1}")
    return coefficients


# 这个函数负责把多项式系数转成方便打印的整数列表。
def polynomial_to_debug_list(coefficients) -> List[int]:
    debug_values: List[int] = []
    index = 0

    while index < len(coefficients):
        debug_values.append(int(coefficients[index]))
        index = index + 1

    return debug_values


# 这个函数负责构造 Shamir 使用的随机多项式 q(x)。
def build_random_polynomial(secret_value: int, threshold: int):
    print("开始构造 Shamir 随机多项式。")
    print("对应公式：q(x) = s + a1*x + a2*x^2 + ... + a_(t-1)*x^(t-1)")

    coefficients = [to_field_element(secret_value, "secret")]
    current_degree = 1

    while current_degree < threshold:
        random_coefficient_int = secrets.randbelow(FIELD_PRIME)
        coefficients.append(FIELD(random_coefficient_int))
        print(f"已生成随机系数 a_{current_degree} = {random_coefficient_int}")
        current_degree = current_degree + 1

    print(f"随机多项式构造完成，系数列表是：{polynomial_to_debug_list(coefficients)}")
    return coefficients


# 这个函数负责在有限域中计算 q(x) 的值。
def evaluate_polynomial(coefficients, x_value):
    print(f"准备计算 q(x)，当前代入的 x = {int(x_value)}")
    print("这一步对应份额生成过程：y = q(x)")

    result = FIELD(0)
    current_power = FIELD(1)
    coefficient_index = 0

    while coefficient_index < len(coefficients):
        current_term = coefficients[coefficient_index] * current_power
        result = result + current_term
        print(
            f"当前处理 a_{coefficient_index}，"
            f"项值 = {int(current_term)}，"
            f"累计结果 = {int(result)}"
        )
        current_power = current_power * x_value
        coefficient_index = coefficient_index + 1

    print(f"q(x) 计算完成，得到 y = {int(result)}")
    return result


# 这个函数负责生成互不相同且非零的评估点 x。
def generate_distinct_x_values(share_count: int):
    print("开始随机生成互不相同的评估点 x。")

    used_x_values = set()
    x_values = []

    while len(x_values) < share_count:
        random_x_int = secrets.randbelow(FIELD_PRIME - 1) + 1

        if random_x_int in used_x_values:
            print(f"遇到重复评估点 x = {random_x_int}，重新抽取。")
            continue

        used_x_values.add(random_x_int)
        x_values.append(FIELD(random_x_int))
        print(f"成功选取评估点 x = {random_x_int}")

    print("所有评估点都已生成完成。")
    return x_values


# 这个函数负责做多项式加法。
def add_polynomials(left_coefficients, right_coefficients):
    print("准备执行多项式加法。")

    max_length = max(len(left_coefficients), len(right_coefficients))
    result = []
    index = 0

    while index < max_length:
        current_value = FIELD(0)

        if index < len(left_coefficients):
            current_value = current_value + left_coefficients[index]

        if index < len(right_coefficients):
            current_value = current_value + right_coefficients[index]

        result.append(current_value)
        index = index + 1

    trimmed_result = trim_polynomial_coefficients(result)
    print(f"多项式加法完成，结果系数是：{polynomial_to_debug_list(trimmed_result)}")
    return trimmed_result


# 这个函数负责做多项式乘法。
def multiply_polynomials(left_coefficients, right_coefficients):
    print("准备执行多项式乘法。")

    result_length = len(left_coefficients) + len(right_coefficients) - 1
    result = []
    index = 0

    while index < result_length:
        result.append(FIELD(0))
        index = index + 1

    left_index = 0
    while left_index < len(left_coefficients):
        right_index = 0
        while right_index < len(right_coefficients):
            result_index = left_index + right_index
            result[result_index] = (
                result[result_index]
                + left_coefficients[left_index] * right_coefficients[right_index]
            )
            right_index = right_index + 1
        left_index = left_index + 1

    trimmed_result = trim_polynomial_coefficients(result)
    print(f"多项式乘法完成，结果系数是：{polynomial_to_debug_list(trimmed_result)}")
    return trimmed_result


# 这个函数负责使用拉格朗日插值恢复完整多项式 q(x)。
def interpolate_polynomial(x_values, y_values):
    print("开始执行拉格朗日插值，准备恢复 q(x)。")
    print("对应公式：q(x) = Σ y_i * L_i(x)")

    result_polynomial = [FIELD(0)]
    outer_index = 0

    while outer_index < len(x_values):
        print(f"正在构造第 {outer_index + 1} 个拉格朗日基多项式。")

        basis_polynomial = [FIELD(1)]
        denominator = FIELD(1)
        inner_index = 0

        while inner_index < len(x_values):
            if inner_index != outer_index:
                factor_polynomial = [FIELD(0) - x_values[inner_index], FIELD(1)]
                basis_polynomial = multiply_polynomials(basis_polynomial, factor_polynomial)
                denominator = denominator * (x_values[outer_index] - x_values[inner_index])
                print(
                    f"已乘入因子 (x - x_{inner_index})，"
                    f"当前分母累计值 = {int(denominator)}"
                )
            inner_index = inner_index + 1

        scale_value = y_values[outer_index] / denominator
        print(f"当前插值分量的缩放因子是：{int(scale_value)}")

        scaled_polynomial = []
        coefficient_index = 0

        while coefficient_index < len(basis_polynomial):
            scaled_polynomial.append(basis_polynomial[coefficient_index] * scale_value)
            coefficient_index = coefficient_index + 1

        result_polynomial = add_polynomials(result_polynomial, scaled_polynomial)
        print(f"当前累加后的多项式系数是：{polynomial_to_debug_list(result_polynomial)}")
        outer_index = outer_index + 1

    final_polynomial = trim_polynomial_coefficients(result_polynomial)
    print(f"插值完成，恢复出的 q(x) 系数是：{polynomial_to_debug_list(final_polynomial)}")
    return final_polynomial


# 这个函数负责把低位在前的系数列表转成 galois.Poly 对象。
def coefficients_to_galois_poly(coefficients):
    print("准备把系数列表转换成 galois.Poly 对象。")

    descending_coefficients = []
    index = len(coefficients) - 1

    while index >= 0:
        descending_coefficients.append(coefficients[index])
        index = index - 1

    polynomial_object = galois.Poly(descending_coefficients, field=FIELD)
    print("galois.Poly 对象构造完成。")
    return polynomial_object


# 这个函数负责把请求中的份额列表解析成后端内部可用结构。
def parse_share_list(raw_shares: List[BasicShareInput], field_name_prefix: str):
    print(f"开始解析份额列表 {field_name_prefix}。")

    if len(raw_shares) == 0:
        raise HTTPException(status_code=400, detail=f"{field_name_prefix} 不能为空。")

    parsed_shares = []
    used_x_values = set()
    index = 0

    while index < len(raw_shares):
        current_share = raw_shares[index]

        if current_share.participant_id <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"{field_name_prefix}[{index}].participant_id 必须是正整数。",
            )

        x_int = parse_big_integer(current_share.x, f"{field_name_prefix}[{index}].x")
        y_int = parse_big_integer(current_share.y, f"{field_name_prefix}[{index}].y")

        if x_int == 0:
            raise HTTPException(
                status_code=400,
                detail=f"{field_name_prefix}[{index}].x 不能为 0。",
            )

        if x_int in used_x_values:
            raise HTTPException(status_code=400, detail=f"{field_name_prefix} 中存在重复的 x。")

        used_x_values.add(x_int)

        parsed_share = {
            "participant_id": current_share.participant_id,
            "x_int": x_int,
            "y_int": y_int,
            "x_field": to_field_element(x_int, f"{field_name_prefix}[{index}].x"),
            "y_field": to_field_element(y_int, f"{field_name_prefix}[{index}].y"),
        }
        parsed_shares.append(parsed_share)

        print(
            f"份额解析完成：participant_id = {current_share.participant_id}，"
            f"x = {x_int}，y = {y_int}"
        )

        index = index + 1

    print(f"{field_name_prefix} 解析完成。")
    return parsed_shares


# 这个函数负责校验 trace_key 的格式是否合法。
def validate_trace_key_items(trace_key: List[TraceKeyItem]):
    print("开始校验 trace_key。")

    if len(trace_key) == 0:
        raise HTTPException(status_code=400, detail="trace_key 不能为空。")

    used_participant_ids = set()
    index = 0

    while index < len(trace_key):
        current_item = trace_key[index]

        if current_item.participant_id <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"trace_key[{index}].participant_id 必须是正整数。",
            )

        if current_item.participant_id in used_participant_ids:
            raise HTTPException(status_code=400, detail="trace_key 中存在重复的 participant_id。")

        if current_item.trace_hash.strip() == "":
            raise HTTPException(status_code=400, detail=f"trace_key[{index}].trace_hash 不能为空。")

        used_participant_ids.add(current_item.participant_id)
        index = index + 1

    print("trace_key 校验通过。")


# 这个函数负责校验 verify_key 的格式是否合法。
def validate_verify_key(verify_key: VerifyKey):
    print("开始校验 verify_key。")

    if verify_key.hash_algorithm.lower() != "sha256":
        raise HTTPException(status_code=400, detail="verify_key.hash_algorithm 目前只支持 sha256。")

    if len(verify_key.participants) == 0:
        raise HTTPException(status_code=400, detail="verify_key.participants 不能为空。")

    used_participant_ids = set()
    index = 0

    while index < len(verify_key.participants):
        current_item = verify_key.participants[index]

        if current_item.participant_id <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"verify_key.participants[{index}].participant_id 必须是正整数。",
            )

        if current_item.participant_id in used_participant_ids:
            raise HTTPException(
                status_code=400,
                detail="verify_key.participants 中存在重复的 participant_id。",
            )

        if current_item.trace_hash.strip() == "":
            raise HTTPException(
                status_code=400,
                detail=f"verify_key.participants[{index}].trace_hash 不能为空。",
            )

        used_participant_ids.add(current_item.participant_id)
        index = index + 1

    print("verify_key 校验通过。")


# 这个函数负责把追踪密钥归一化成稳定签名，方便做内存匹配。
def normalize_trace_key_signature(trace_key: List[TraceKeyItem]):
    print("准备把 trace_key 归一化成稳定签名。")

    signature = []
    index = 0

    while index < len(trace_key):
        current_item = trace_key[index]
        signature.append((current_item.participant_id, current_item.trace_hash))
        index = index + 1

    signature.sort(key=lambda item: item[0])
    print("trace_key 稳定签名构造完成。")
    return tuple(signature)


# 这个函数负责把解析后的份额列表转成可比较的稳定集合签名。
def build_share_signature(parsed_shares):
    print("准备把份额列表转换成稳定签名。")

    signature = set()
    index = 0

    while index < len(parsed_shares):
        current_item = parsed_shares[index]
        signature.add(
            (
                current_item["participant_id"],
                str(current_item["x_int"]),
                str(current_item["y_int"]),
            )
        )
        index = index + 1

    print("份额稳定签名构造完成。")
    return signature


# 这个函数负责把刚生成的分发结果记录到内存中。
def record_issued_session(response: ShareResponse):
    print("准备把本轮分发结果记录到内存中。")

    session_record = {
        "threshold": response.threshold,
        "shares": set(),
        "trace_key_signature": normalize_trace_key_signature(response.trace_key),
    }

    index = 0
    while index < len(response.shares):
        current_share = response.shares[index]
        session_record["shares"].add(
            (current_share.participant_id, current_share.x, current_share.y)
        )
        index = index + 1

    ISSUED_SESSIONS.append(session_record)

    while len(ISSUED_SESSIONS) > MAX_ISSUED_SESSIONS:
        ISSUED_SESSIONS.pop(0)

    print(
        f"本轮分发结果已经记录到内存。"
        f"当前缓存轮数 = {len(ISSUED_SESSIONS)}，"
        f"该轮门限 = {response.threshold}"
    )


# 这个函数负责根据份额列表尝试匹配内存中的历史分发记录。
def find_matching_session_by_shares(parsed_shares):
    print("准备根据份额列表查找匹配的历史分发记录。")

    share_signature = build_share_signature(parsed_shares)
    matched_sessions = []
    index = 0

    while index < len(ISSUED_SESSIONS):
        current_session = ISSUED_SESSIONS[index]
        if share_signature.issubset(current_session["shares"]):
            matched_sessions.append(current_session)
        index = index + 1

    if len(matched_sessions) == 0:
        print("没有找到匹配的历史分发记录，后续将走无状态兜底校验。")
        return None

    print(f"找到 {len(matched_sessions)} 条匹配的历史分发记录，默认使用最新一条。")
    return matched_sessions[-1]


# 这个函数负责根据 trace_key 尝试匹配内存中的历史分发记录。
def find_matching_session_by_trace_key(trace_key: List[TraceKeyItem]):
    print("准备根据 trace_key 查找匹配的历史分发记录。")

    target_signature = normalize_trace_key_signature(trace_key)
    index = len(ISSUED_SESSIONS) - 1

    while index >= 0:
        current_session = ISSUED_SESSIONS[index]
        if current_session["trace_key_signature"] == target_signature:
            print("成功找到与 trace_key 对应的历史分发记录。")
            return current_session
        index = index - 1

    print("没有找到与 trace_key 对应的历史分发记录。")
    return None


# 这个函数负责优先处理一次和二次多项式的有限域求根。
def find_small_degree_roots(polynomial_coefficients):
    degree = len(polynomial_coefficients) - 1
    print(f"准备尝试教学版快速求根，当前多项式次数是：{degree}")

    if degree == 1:
        constant_term = polynomial_coefficients[0]
        linear_term = polynomial_coefficients[1]
        root_value = (FIELD(0) - constant_term) / linear_term
        root_int_values = [int(root_value)]
        print(f"一次多项式求根完成，候选根是：{root_int_values}")
        return root_int_values

    if degree == 2:
        constant_term = polynomial_coefficients[0]
        linear_term = polynomial_coefficients[1]
        quadratic_term = polynomial_coefficients[2]
        two_a = FIELD(2) * quadratic_term
        discriminant = linear_term * linear_term - FIELD(4) * quadratic_term * constant_term

        print(f"二次多项式判别式是：{int(discriminant)}")

        if discriminant == FIELD(0):
            repeated_root = (FIELD(0) - linear_term) / two_a
            root_int_values = [int(repeated_root)]
            print(f"二次多项式只有一个重根：{root_int_values}")
            return root_int_values

        sqrt_candidate = discriminant ** ((FIELD_PRIME + 1) // 4)
        if sqrt_candidate * sqrt_candidate != discriminant:
            print("判别式不是平方剩余，当前二次多项式在有限域中没有根。")
            return []

        root_one = ((FIELD(0) - linear_term) + sqrt_candidate) / two_a
        root_two = ((FIELD(0) - linear_term) - sqrt_candidate) / two_a
        root_int_values = sorted(list({int(root_one), int(root_two)}))
        print(f"二次多项式求根完成，候选根是：{root_int_values}")
        return root_int_values

    print("当前多项式次数大于 2，快速求根不适用，将回退到 galois.Poly.roots()。")
    return None


# 这个函数负责在参考多项式上构造 q(x) - leaked_y 并求根。
def find_candidate_x_values(polynomial_coefficients, leaked_y_int: int):
    print(f"开始构造 q(x) - leaked_y，当前 leaked_y = {leaked_y_int}")
    print("这一步对应有限域中的求根过程。")

    leaked_y_field = to_field_element(leaked_y_int, "leaked_y")
    adjusted_coefficients = []
    index = 0

    while index < len(polynomial_coefficients):
        current_value = polynomial_coefficients[index]
        if index == 0:
            current_value = current_value - leaked_y_field
        adjusted_coefficients.append(current_value)
        index = index + 1

    adjusted_coefficients = trim_polynomial_coefficients(adjusted_coefficients)
    print(f"q(x) - leaked_y 的系数是：{polynomial_to_debug_list(adjusted_coefficients)}")

    is_zero_polynomial = True
    index = 0

    while index < len(adjusted_coefficients):
        if adjusted_coefficients[index] != FIELD(0):
            is_zero_polynomial = False
            break
        index = index + 1

    if is_zero_polynomial:
        print("出现零多项式，说明当前 leaked_y 对所有 x 都成立，无法唯一追踪。")
        return {"all_points_match": True, "roots": []}

    if len(adjusted_coefficients) == 1:
        print("当前是非零常数多项式，没有任何根。")
        return {"all_points_match": False, "roots": []}

    small_degree_roots = find_small_degree_roots(adjusted_coefficients)
    if small_degree_roots is not None:
        return {"all_points_match": False, "roots": small_degree_roots}

    galois_polynomial = coefficients_to_galois_poly(adjusted_coefficients)
    print("准备调用 galois.Poly.roots() 在有限域中求根。")

    try:
        root_field_values = galois_polynomial.roots()
    except Exception as error:
        print(f"有限域求根失败，错误信息：{error}")
        raise HTTPException(status_code=500, detail="有限域求根失败，请查看后端日志。") from error

    root_int_values = []
    index = 0

    while index < len(root_field_values):
        root_int_values.append(int(root_field_values[index]))
        index = index + 1

    root_int_values.sort()
    print(f"求根完成，候选 x 值是：{root_int_values}")
    return {"all_points_match": False, "roots": root_int_values}


# 这个函数负责把候选根和 trace_key 做哈希匹配。
def match_roots_with_trace_key(candidate_x_values: List[int], trace_key: List[TraceKeyItem]):
    print("开始把候选 x 值和 trace_key 做哈希匹配。")

    matched_participant_ids: List[int] = []
    matched_x_by_participant: Dict[int, int] = {}
    candidate_index = 0

    while candidate_index < len(candidate_x_values):
        candidate_x_int = candidate_x_values[candidate_index]
        candidate_hash = hash_x_value(candidate_x_int)
        trace_index = 0

        while trace_index < len(trace_key):
            current_trace_item = trace_key[trace_index]
            if current_trace_item.trace_hash == candidate_hash:
                matched_participant_ids.append(current_trace_item.participant_id)
                matched_x_by_participant[current_trace_item.participant_id] = candidate_x_int
                print(
                    f"哈希匹配成功：participant_id = {current_trace_item.participant_id}，"
                    f"x = {candidate_x_int}"
                )
            trace_index = trace_index + 1

        candidate_index = candidate_index + 1

    matched_participant_ids = sorted(list(set(matched_participant_ids)))
    print(f"哈希匹配完成，命中的参与者 ID 列表是：{matched_participant_ids}")
    return matched_participant_ids, matched_x_by_participant


# 这个函数负责在 verify_key 中找到某个嫌疑人的目标哈希。
def find_expected_hash(verify_key: VerifyKey, suspect_participant_id: int) -> str:
    print(f"准备在 verify_key 中查找嫌疑人 {suspect_participant_id} 的目标哈希。")

    index = 0
    while index < len(verify_key.participants):
        current_item = verify_key.participants[index]
        if current_item.participant_id == suspect_participant_id:
            print("成功找到嫌疑人的目标哈希。")
            return current_item.trace_hash
        index = index + 1

    raise HTTPException(status_code=400, detail="verify_key 中找不到这个嫌疑人 ID。")


# 这个根接口用于快速确认后端是否已经启动。
@app.get("/")
def read_root():
    print("收到根路径请求，返回后端欢迎信息。")
    return {
        "message": "教学版可追踪秘密共享后端已启动。",
        "field_prime": str(FIELD_PRIME),
    }


# 这个接口负责执行秘密分发。
@app.post("/api/share", response_model=ShareResponse)
def create_shares(request: ShareRequest):
    print("收到 /api/share 请求。")
    print(f"原始请求数据：{request.model_dump()}")

    secret_int = parse_big_integer(request.secret, "secret")

    if request.share_count <= 0:
        raise HTTPException(status_code=400, detail="share_count 必须是正整数。")

    if request.threshold <= 0:
        raise HTTPException(status_code=400, detail="threshold 必须是正整数。")

    if request.threshold > request.share_count:
        raise HTTPException(status_code=400, detail="threshold 不能大于 share_count。")

    to_field_element(secret_int, "secret")

    polynomial_coefficients = build_random_polynomial(secret_int, request.threshold)
    x_values = generate_distinct_x_values(request.share_count)

    share_items: List[ShareItem] = []
    trace_key_items: List[TraceKeyItem] = []
    verify_key_items: List[VerifyParticipantItem] = []
    index = 0

    while index < len(x_values):
        participant_id = index + 1
        x_field = x_values[index]
        y_field = evaluate_polynomial(polynomial_coefficients, x_field)
        x_int = int(x_field)
        y_int = int(y_field)
        trace_hash = hash_x_value(x_int)

        share_items.append(
            ShareItem(
                participant_id=participant_id,
                x=str(x_int),
                y=str(y_int),
                trace_hash=trace_hash,
            )
        )
        trace_key_items.append(
            TraceKeyItem(
                participant_id=participant_id,
                trace_hash=trace_hash,
            )
        )
        verify_key_items.append(
            VerifyParticipantItem(
                participant_id=participant_id,
                trace_hash=trace_hash,
            )
        )

        print(
            f"已生成份额：participant_id = {participant_id}，"
            f"x = {x_int}，y = {y_int}，trace_hash = {trace_hash}"
        )
        index = index + 1

    response = ShareResponse(
        field_prime=str(FIELD_PRIME),
        secret=str(secret_int),
        share_count=request.share_count,
        threshold=request.threshold,
        shares=share_items,
        trace_key=trace_key_items,
        verify_key=VerifyKey(
            hash_algorithm="sha256",
            participants=verify_key_items,
        ),
    )

    record_issued_session(response)
    print("秘密分发完成，准备返回响应。")
    return response


# 这个接口负责用输入份额恢复秘密 q(0)。
@app.post("/api/rec", response_model=ReconstructResponse)
def reconstruct_secret(request: ReconstructRequest):
    print("收到 /api/rec 请求。")
    print(f"原始请求数据：{request.model_dump()}")

    parsed_shares = parse_share_list(request.shares, "shares")
    matched_session = find_matching_session_by_shares(parsed_shares)

    if matched_session is not None:
        required_share_count = matched_session["threshold"]
        print(f"当前份额匹配到历史分发记录，门限是：{required_share_count}")
        if len(parsed_shares) < required_share_count:
            raise HTTPException(
                status_code=400,
                detail=f"份额数量不足，至少需要 {required_share_count} 个份额才能恢复秘密。",
            )
    elif len(parsed_shares) < 2:
        raise HTTPException(
            status_code=400,
            detail="份额数量不足，至少需要 2 个份额才能进行教学版插值恢复。",
        )

    x_values = []
    y_values = []
    index = 0

    while index < len(parsed_shares):
        x_values.append(parsed_shares[index]["x_field"])
        y_values.append(parsed_shares[index]["y_field"])
        index = index + 1

    recovered_polynomial = interpolate_polynomial(x_values, y_values)
    recovered_secret = recovered_polynomial[0]

    print(f"秘密重构完成，恢复出的 q(0) = {int(recovered_secret)}")
    return ReconstructResponse(recovered_secret=serialize_field_value(recovered_secret))


# 这个接口负责在教学版完美黑盒模型下追踪叛徒。
@app.post("/api/trace", response_model=TraceResponse)
def trace_traitor(request: TraceRequest):
    print("收到 /api/trace 请求。")
    print(f"原始请求数据：{request.model_dump()}")

    validate_trace_key_items(request.trace_key)

    if len(request.leaked_outputs) == 0:
        raise HTTPException(status_code=400, detail="leaked_outputs 不能为空。")

    parsed_reference_shares = parse_share_list(request.reference_shares, "reference_shares")
    matched_session = find_matching_session_by_trace_key(request.trace_key)

    if matched_session is not None:
        reference_share_signature = build_share_signature(parsed_reference_shares)
        if not reference_share_signature.issubset(matched_session["shares"]):
            raise HTTPException(
                status_code=400,
                detail="reference_shares 与 trace_key 不属于同一轮分发结果。",
            )

        required_share_count = matched_session["threshold"]
        print(f"当前 trace_key 匹配到历史分发记录，门限是：{required_share_count}")
        if len(parsed_reference_shares) < required_share_count:
            raise HTTPException(
                status_code=400,
                detail=f"参考份额数量不足，至少需要 {required_share_count} 个合法参考份额才能恢复 q(x)。",
            )
    elif len(parsed_reference_shares) < 2:
        raise HTTPException(
            status_code=400,
            detail="参考份额数量不足，至少需要 2 个参考份额才能进行教学版插值恢复。",
        )

    x_values = []
    y_values = []
    index = 0

    while index < len(parsed_reference_shares):
        x_values.append(parsed_reference_shares[index]["x_field"])
        y_values.append(parsed_reference_shares[index]["y_field"])
        index = index + 1

    recovered_polynomial = interpolate_polynomial(x_values, y_values)

    evidence_items: List[EvidenceItem] = []
    successful_participant_ids: List[int] = []
    has_ambiguous_case = False
    leaked_index = 0

    while leaked_index < len(request.leaked_outputs):
        leaked_y_int = parse_big_integer(
            request.leaked_outputs[leaked_index].leaked_y,
            f"leaked_outputs[{leaked_index}].leaked_y",
        )

        root_result = find_candidate_x_values(recovered_polynomial, leaked_y_int)
        candidate_x_values = root_result["roots"]
        matched_participant_ids: List[int] = []
        proof_x_text: Optional[str] = None

        if root_result["all_points_match"]:
            print("当前 leaked_y 造成零多项式，证据不唯一。")
            has_ambiguous_case = True
        else:
            matched_participant_ids, matched_x_by_participant = match_roots_with_trace_key(
                candidate_x_values,
                request.trace_key,
            )

            if len(matched_participant_ids) == 1:
                participant_id = matched_participant_ids[0]
                successful_participant_ids.append(participant_id)
                proof_x_text = str(matched_x_by_participant[participant_id])
                print(
                    f"当前 leaked_y 已唯一锁定参与者 {participant_id}，"
                    f"proof_x = {proof_x_text}"
                )
            elif len(matched_participant_ids) > 1:
                print("当前 leaked_y 匹配到多个参与者，证据不唯一。")
                has_ambiguous_case = True
            else:
                print("当前 leaked_y 没有匹配到任何参与者。")

        candidate_x_texts = []
        candidate_index = 0

        while candidate_index < len(candidate_x_values):
            candidate_x_texts.append(str(candidate_x_values[candidate_index]))
            candidate_index = candidate_index + 1

        evidence_items.append(
            EvidenceItem(
                leaked_y=str(leaked_y_int),
                candidate_x_values=candidate_x_texts,
                matched_participant_ids=matched_participant_ids,
                proof_x=proof_x_text,
            )
        )

        leaked_index = leaked_index + 1

    distinct_successful_ids = sorted(list(set(successful_participant_ids)))
    trace_result = "not_found"
    traitor_id: Optional[int] = None

    if has_ambiguous_case:
        trace_result = "ambiguous"
    elif len(distinct_successful_ids) == 1:
        trace_result = "success"
        traitor_id = distinct_successful_ids[0]
    elif len(distinct_successful_ids) > 1:
        trace_result = "ambiguous"

    print(f"叛徒追踪结束，trace_result = {trace_result}，traitor_id = {traitor_id}")
    return TraceResponse(
        trace_result=trace_result,
        traitor_id=traitor_id,
        evidence=evidence_items,
    )


# 这个接口负责验证 proof_x 是否真的属于某个嫌疑人。
@app.post("/api/verify", response_model=VerifyResponse)
def verify_proof(request: VerifyRequest):
    print("收到 /api/verify 请求。")
    print(f"原始请求数据：{request.model_dump()}")

    validate_verify_key(request.verify_key)

    if request.suspect_participant_id <= 0:
        raise HTTPException(status_code=400, detail="suspect_participant_id 必须是正整数。")

    proof_x_int = parse_big_integer(request.proof_x, "proof_x")

    if proof_x_int <= 0:
        raise HTTPException(status_code=400, detail="proof_x 必须是正整数。")

    to_field_element(proof_x_int, "proof_x")

    expected_hash = find_expected_hash(request.verify_key, request.suspect_participant_id)
    provided_hash = hash_x_value(proof_x_int)

    if expected_hash == provided_hash:
        print("验证通过：Hash(proof_x) 与验证密钥中的哈希一致。")
        return VerifyResponse(
            verified=True,
            expected_hash=expected_hash,
            provided_hash=provided_hash,
            message="验证通过：这份证据和嫌疑人的验证密钥一致。",
        )

    print("验证拒绝：Hash(proof_x) 与验证密钥中的哈希不一致。")
    return VerifyResponse(
        verified=False,
        expected_hash=expected_hash,
        provided_hash=provided_hash,
        message="验证拒绝：这份证据无法通过哈希匹配。",
    )
