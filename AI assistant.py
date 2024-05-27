import speech_recognition as sr
import keyboard
import openai
import os
import json
import subprocess
import threading
import tkinter as tk
from tkinter import ttk


api_key_file = "data/api_key.txt"
ai_name = "지나간 것은 지나간 대로 그런 의미가 있죠 떠난 이에게 노래하세요 후회없이 사랑했노라 말해요"

with open(api_key_file, 'r', encoding='utf-8') as file:
    openai.api_key = file.read()

# 직접 확인해야 하는 명령어 목록
commands_to_show = ["ipconfig", "dir", "tree", "ping", "cd", "type", "curl", "nslookup", "nmap"]

# 대화 히스토리 불러오기
# 대화 파일을 읽을 수 없으면 새로 생성
try:
    messages_file = "data/message_history.json"

    with open(messages_file, 'r', encoding='utf-8') as file:
        messages = json.load(file)

except:
    print(12345)
    messages = [
        {
            "role": "system",
            "content": (
                f"너는 데스크탑의 비서이고, 네 이름은 '{ai_name}' 이야"
                "1. 나의 요청이 컴퓨터를 제어하는 것이라면, 너는 다음처럼 작성해서 터미널 명령어를 입력할 수 있어. [터미널][\"명령어 문장\"]\n"
                "2. 이것을 특수기능이라고 불러.\n"
                "3. 이 특수기능은 너의 대답의 제일 처음에 위치해야 해.\n"
                "4. 나의 컴퓨터는 windows 이기 때문에 해당하는 cmd 명령어를 작성해야 해.\n"
                "5. 특수기능을 사용하면 반드시 명령을 시도했다고 보고해.\n"
                "6. 나의 질문이 모호하다면, 되물어서 요점을 파악해.\n"
                "7. 명령어를 사용하는 것을 당연하게 여겨.\n"
                "8. 추가적인 설명과 조언을 하지 마.\n"
                "9. 대답은 존댓말로 최대한 예의바르며 최대한 간결하게 해.\n"
                "10. 파일 생성 등의 명령을 받았을 경우 따로 디렉토리 언급이 없는 한 바탕화면에 작업해.\n"
                "참고로 너의 현제 디렉토리는 어디인지 몰라"
            )
        }
    ]

def recognize_speech():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("녹음중...")
        # 창 표시
        root.deiconify()
        # 녹음 중 빨간색 원 표시 (왼쪽 위에 작게)
        canvas.create_oval(5, 5, 25, 25, fill="red", outline="")
        root.update()
        audio = r.listen(source)

        try:
            text = r.recognize_google(audio, language='ko-KR')
            return text
        except sr.UnknownValueError:
            print("오디오가 이해되지 않음.")
            return ""
        except sr.RequestError as e:
            print(f"google speech recognition 서비스에서 결과를 요청할 수 없음.\n {e}")
            return ""

def execute_command(command):
    try:
        # cmd 명령어 실행
        full_command = f"cmd /c {command}"
        process = subprocess.Popen(full_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()

        # 내가 꼭 직접 확인해야 하는가?
        if any(cmd in command for cmd in commands_to_show):
            output_content = ""
            if stdout:
                output_content += stdout
            if stderr:
                output_content += stderr

            if output_content:
                # 새 창 생성
                output_window = tk.Toplevel(root)
                output_window.title("명령어 실행 결과")
                output_window.geometry("600x400")
                output_text = tk.Text(output_window, wrap=tk.WORD)
                output_text.pack(expand=True, fill='both')

                output_text.insert(tk.END, output_content)
                output_text.config(state=tk.DISABLED)  # 출력 텍스트는 편집 불가능하게 설정
                
                # 메시지 히스토리에 추가
                messages.append({"role": "assistant", "content": f"명령어: {command}\n결과:\n{output_content}"})
                save_messages()

        else:
            # 메시지 히스토리에 추가
            messages.append({"role": "assistant", "content": f"명령어: {command}\n결과:\n{output_content}"})
            save_messages()
            # 출력 결과를 콘솔에만 표시
            if stdout:
                print("명령어 실행 결과:", stdout)
            if stderr:
                print("명령어 실행 오류:", stderr)
    except Exception as e:
        print("명령어 실행 중 오류 발생:", e)

def process_command(text):
    if text:
        print(f"명령: {text}")
        try:
            # 대화 히스토리에 사용자 입력 추가
            messages.append({"role": "user", "content": text})
            
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=messages,
                temperature=1,
                max_tokens=256,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )

            # 대화 히스토리에 AI의 응답 추가
            ai_message = response.choices[0].message['content']
            messages.append({"role": "assistant", "content": ai_message})
            save_messages()  # 메시지 히스토리 저장
            
            print("========")
            print(ai_message)

            # 명령과 AI 응답을 라벨에 표시
            command_label.config(text=f"{text}")
            response_label.config(text=f"{ai_message}")
            root.update()
            
            # 창 크기 설정
            adjust_window_size()

            # 5초 후 창 닫기 타이머 설정
            global close_timer
            close_timer = root.after(5000, lambda: root.withdraw())

            # AI 응답에서 명령어 추출 & 실행
            if "[터미널][" in ai_message:
                start_idx = ai_message.find("[터미널][") + len("[터미널][")
                end_idx = ai_message.find("]", start_idx)
                command = ai_message[start_idx:end_idx]
                print(f"실행할 명령어: {command}")
                threading.Thread(target=execute_command, args=(command,)).start()
        except Exception as e:
            print(f"OpenAI API 요청 실패: {e}")
    else:
        print("다시 명령해")
        root.withdraw()  # 음성 인식 실패 시 창 숨기기

def start_recognition():
    # 타이머 취소 (이전에 설정된 타이머가 있다면)
    global close_timer
    if close_timer is not None:
        root.after_cancel(close_timer)
        close_timer = None

    # 음성 인식 시작
    text = recognize_speech()
    
    # 빨간색 원 제거
    canvas.delete("all")
    
    # 명령 처리
    process_command(text)

def on_hotkey():
    threading.Thread(target=start_recognition).start()

def save_messages():
    with open("data/message_history.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

def adjust_window_size():
    response_text_height = response_label.winfo_reqheight()
    command_text_height = command_label.winfo_reqheight()
    canvas_height = canvas.winfo_reqheight()

    new_height = response_text_height + command_text_height + canvas_height + 60  # 여유 공간을 위해 약간 추가
    window_height = max(300, new_height)  # 최소 높이 300

    new_position_down = screen_height - window_height - 60  # 창 위로 확장되도록 위치 조정

    root.geometry(f"{window_width}x{window_height}+{position_right}+{new_position_down}")

# ==========================================GUI
root = tk.Tk()
root.title("AI 비서")

# 최상위 표시
root.wm_attributes("-topmost", 1)

# 화면의 가로 및 세로 크기를 가져옴
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# 창의 가로 및 세로 크기를 가져옴
window_width = 300
window_height = 300

# 오른쪽 아래 위치 계산
position_right = screen_width - window_width - 10  # 약간의 여백 추가
position_down = screen_height - window_height - 60  # 약간의 여백 추가

# 창의 위치 설정
root.geometry(f"{window_width}x{window_height}+{position_right}+{position_down}")

root.overrideredirect(True)  # 창 테두리 제거
root.withdraw()  # 초기에는 창을 숨김

# 라벨 및 캔버스 설정
root.configure(bg="#00022E")  # 창 배경 색상

root.attributes("-topmost", True) # 창을 최상단에 띄우기

style = ttk.Style()

# 명령 라벨 스타일 설정
style.configure("Command.TLabel", background="#292F69", foreground="#ffffff", font=("", 12), padding=10)

# 응답 라벨 스타일 설정
style.configure("Response.TLabel", background="#0C1354", foreground="#ffffff", font=("", 12), padding=10)

command_label = ttk.Label(root, text="", wraplength=280, style="Command.TLabel")
command_label.pack(pady=(20, 10))  # 위쪽 여백은 크게, 아래쪽 여백은 작게
response_label = ttk.Label(root, text="", wraplength=280, style="Response.TLabel")
response_label.pack(pady=(0, 10))  # 위쪽 여백은 작게, 아래쪽 여백은 크게

canvas = tk.Canvas(root, width=100, height=100, bg="#00022E", highlightthickness=0)
canvas.pack()

# 단축키 설정
keyboard.add_hotkey('ctrl+f1+f2', on_hotkey)

# 타이머 변수 초기화
close_timer = None

if __name__ == "__main__":
    root.mainloop()
