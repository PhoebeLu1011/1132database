# 1132資料結構

# 目錄
### HW1
* [程式碼](https://github.com/PhoebeLu1011/1132database/blob/main/DatatreatAgentAutogen.py)
* [架構圖](#架構圖)
* [抽換數據](#抽換數據)
* [AIAGENT種類的使用](#AIAGENT的使用)

## HW1
### 架構圖
![圖片描述](images/image01.png)
### 抽換數據

| PatientID | Name         | Age | Gender | InjuryType       | Severity | MRI_Result           | XRay_Result          | Blood_Test_Result           | Recommended_Treatment                  |
|-----------|-------------|-----|--------|------------------|----------|----------------------|----------------------|-----------------------------|----------------------------------------|
| 1         | John Doe    | 45  | M      | ACL Tear         | Severe   | Complete tear        | Normal               | Normal                      | Physical therapy, possible surgery    |
| 2         | Jane Smith  | 32  | F      | Fractured Wrist  | Moderate | No abnormalities     | Fracture on radius   | Normal                      | Cast immobilization, pain management  |
| 3         | Michael Lee | 28  | M      | Concussion       | Mild     | No abnormalities     | Normal               | Elevated white blood cells  | Rest, cognitive therapy               |
| 4         | Sarah Kim   | 60  | F      | Hip Arthritis    | Severe   | Cartilage degeneration | Normal               | Normal                      | Physical therapy, pain management     |
| 5         | David Brown | 50  | M      | Rotator Cuff Tear | Moderate | Partial tear         | Normal               | Normal                      | Strength training, possible surgery   |
| 6         | Emily White | 40  | F      | Herniated Disc   | Severe   | Disc protrusion      | Normal               | Normal                      | Physical therapy, spinal injections   |
 
### AIAGENT的使用

DataAgent : 負責處理與整理數據。\
MultimodalWebSurfer : 透過網路搜尋最新的復健與治療資訊。\
Assistant : 提供初步治療建議。\
UserProxy : 模擬使用者，協助溝通。

```
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
```



本作業是利用 RoundRobinGroupChat 將四個代理人（DataAgent、MultimodalWebSurfer、Assistant 與 UserProxy）組成團隊並協作對話，分批處理 CSV 資料，並要求 MultimodalWebSurfer 搜尋外部網站，納入最新的復健治療建議資訊，最終將所有對話內容整合並輸出為 CSV。

## 功能介紹

透過 RoundRobinGroupChat 機制，讓多個AI Agents合作完成任務：

1.使用 pandas 讀取病患復健數據，並分批處理。

2.利用多個AI Agent來合作處理病患病歷。

3.將分析結果存成 .CSV 檔案輸出。


## 程式碼

1.載入 Python 模組
```
import os
import asyncio
import pandas as pd
from dotenv import load_dotenv
import io
```
2.匯入Autogen 的 AI Agents
```
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
```

3.process_chunk 函式

負責處理單一批次資料，並執行AI Agent。

(1) 轉換資料格式

將 CSV 讀取的 DataFrame 轉換為dict格式。

` hunk_data = chunk.to_dict(orient='records') `


(2) 建立Prompt

生成目前處理的資料範圍、復健分析請求，以及請求 MultimodalWebSurfer 代理人進行網路搜尋的提示。
```
prompt = (
    f"目前正在處理第 {start_idx} 至 {start_idx + len(chunk) - 1} 筆資料（共 {total_records} 筆）。\n"
    f"以下為該批次資料:\n{chunk_data}\n\n"
    "請根據以上資料進行分析，並提供完整的復健治療建議。"
    "其中請特別注意：\n"
    "  1. 分析傷者的傷勢與治療復健需求；\n"
    "  2. 請 MultimodalWebSurfer 搜尋外部網站，找出最新的相關症狀治療建議資訊，\n"
    "     並將搜尋結果整合進回覆中；\n"
    "  3. 最後請提供具體的建議和相關參考資訊，並且如果有相關網站連結請提供。\n"
    "請各代理人協同合作，提供一份完整且具參考價值的建議。"
)
```

(3) 初始化代理人

為每個批次建立新的 AI Agent，確保能夠一同合作並有效處理任務。
```
local_data_agent = AssistantAgent("data_agent", model_client)
local_web_surfer = MultimodalWebSurfer("web_surfer", model_client)
local_assistant = AssistantAgent("assistant", model_client)
local_user_proxy = UserProxyAgent("user_proxy")
```
(4) 建立Team並執行

使用 RoundRobinGroupChat，讓代理人輪流處理任務，直到滿足終止條件。
```
local_team = RoundRobinGroupChat(
    [local_data_agent, local_web_surfer, local_assistant, local_user_proxy],
    termination_condition=termination_condition
)
```
(5) 收集回應
```
messages = []
async for event in local_team.run_stream(task=prompt):
    if isinstance(event, TextMessage):
        print(f"[{event.source}] => {event.content}\n")
        messages.append({
            "batch_start": start_idx,
            "batch_end": start_idx + len(chunk) - 1,
            "source": event.source,
            "content": event.content,
            "type": event.type,
            "prompt_tokens": event.models_usage.prompt_tokens if event.models_usage else None,
            "completion_tokens": event.models_usage.completion_tokens if event.models_usage else None
        })
return messages
```

4.main 函式

(1) 讀取環境變數並初始化模型用戶端
```
gemini_api_key = os.environ.get("GEMINI_API_KEY")
if not gemini_api_key:
    print("請檢查 .env 檔案中的 GEMINI_API_KEY。")
    return

model_client = OpenAIChatCompletionClient(
    model="gemini-2.0-flash",
    api_key=gemini_api_key,
)
```
(2) 使用 pandas 以 chunksize 方式讀取 CSV
```
csv_file_path = "rehabilitation_patient_data.csv"
chunk_size = 1000
chunks = list(pd.read_csv(csv_file_path, chunksize=chunk_size))
total_records = sum(chunk.shape[0] for chunk in chunks)
```
3. 利用 map 與 asyncio.gather同時處理批次
```
tasks = list(map(
    lambda idx_chunk: process_chunk(
        idx_chunk[1],
        idx_chunk[0] * chunk_size,
        total_records,
        model_client,
        termination_condition
    ),
    enumerate(chunks)
))

results = await asyncio.gather(*tasks)
```

(4) 將結果存成 CSV，輸出對話紀錄
```
all_messages = [msg for batch in results for msg in batch]
df_log = pd.DataFrame(all_messages)
output_file = "all_conversation_log.csv"
df_log.to_csv(output_file, index=False, encoding="utf-8-sig")
print(f"已將所有對話紀錄輸出為 {output_file}")
```
(5)結果輸出

最終生成的 all_conversation_log.csv 包含:
每個病患的復健分析與建議、最新搜尋到的復健治療方法。



  


