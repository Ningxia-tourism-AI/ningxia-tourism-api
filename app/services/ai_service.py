from openai import OpenAI

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

# 初始化模型客户端
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=60.0)

SYSTEM_PLAIN = """
你是宁夏文旅智能助手。

你的主要职责：
1. 介绍宁夏旅游景区。
2. 推荐宁夏特色美食。
3. 帮助用户规划旅游路线。
4. 解答宁夏地方文化问题。

请使用自然、准确、易懂的中文回答。
不要编造没有依据的门票价格、开放时间和交通信息。
"""

SYSTEM_WITH_CONTEXT = """你是宁夏文旅智能助手，回答必须严格依据下面提供的【景区数据】。

规则：
1. 数据里有的信息才回答；数据里没有的（门票价格、开放时间、电话、交通）不要编造，直接说“暂未收录”。
2. 涉及数量、筛选、排序的问题，一律以数据为准，不要自己估算。
3. 用简洁自然的中文回答，列表类问题用短列表。
4. 宁夏方言词义、方言翻译也属于你的职责范围；词库未收录时可给出推测，但必须标注“词库未收录，以下为推测”，并说明地区差异；
5. 问题与宁夏文旅（含方言）无关时，礼貌说明只负责宁夏文旅相关问题。"""


def ask_ai(question: str) -> str:
    """原有的普通问答（不带资料）。"""
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PLAIN},
            {"role": "user", "content": question},
        ],
        stream=False,
    )
    return response.choices[0].message.content


def ask_with_context(question: str, context: str) -> str:
    """把检索到的景区数据作为上下文，交给 DeepSeek 组织答案。"""
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_WITH_CONTEXT},
            {"role": "system", "content": f"【景区数据】\n{context}"},
            {"role": "user", "content": question},
        ],
        stream=False,
        temperature=0.3,
    )
    return response.choices[0].message.content
