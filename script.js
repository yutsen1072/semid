const API_URL = 'http://127.0.0.1:8000';

async function fetchSubmissions() {
    try {
        const response = await fetch(`${API_URL}/api/submissions`);
        const data = await response.json();
        console.log("取得所有稿件：", data);
    } catch (error) {
        console.error("連線錯誤：", error);
    }
}

fetchSubmissions();