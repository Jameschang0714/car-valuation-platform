
# 專案部署指南 (Deployment Guide)

本指南將協助您將此鑑價平台部署到 Streamlit Cloud，讓您的員工可以透過網路訪問。

## 第一步：準備 GitHub 儲存庫

1.  登入您的 [GitHub](https://github.com/) 帳號。
2.  點擊右上角的 **+** 號，選擇 **New repository**。
3.  **Repository name** 輸入：`car-valuation-platform` (或您喜歡的名字)。
4.  **Privacy** 建議選擇 **Public** (Streamlit Community Cloud 免費版通常需要 Public，若您有付費版可選 Private)。
5.  其他選項 (Add a README, .gitignore 等) **都不要勾選**，因為我們已經在本地準備好了。
6.  點擊 **Create repository**。

## 第二步：將程式碼上傳至 GitHub

在您剛剛建立的 GitHub 頁面中，您會看到 "…or push an existing repository from the command line" 的區塊。請**依序**複製並執行以下指令 (在您的 VS Code 下方 Terminal 執行)：

```bash
git branch -M main
git remote add origin https://github.com/<您的使用者名稱>/car-valuation-platform.git
git push -u origin main
```
*(注意：請將 `<您的使用者名稱>` 替換為您的 GitHub 帳號名稱，或者直接從 GitHub 頁面上複製整段指令)*

## 第三步：部署至 Streamlit Cloud

1.  前往 [Streamlit Cloud](https://share.streamlit.io/) 並登入 (建議使用 GitHub 帳號登入)。
2.  點擊右上角的 **New app**。
3.  **Repository**: 選擇您剛剛上傳的 `car-valuation-platform`。
4.  **Branch**: 選擇 `main`。
5.  **Main file path**: 選擇 `app.py`。
6.  點擊 **Deploy!**。

## 第四步：等待與測試

Streamlit 會開始安裝必要的套件 (根據 `requirements.txt`) 並啟動應用程式。這可能需要幾分鐘。
部署成功後，您會獲得一個網址 (例如 `https://car-valuation-platform.streamlit.app`)，您可以將此網址分享給您的員工使用。

## 常見問題

- **應用程式啟動失敗？**
    - 點擊右下角的 "Manage app" -> "Logs" 查看錯誤訊息。
    - 通常是 `requirements.txt` 缺少套件，請檢查 Log 並補上。

- **只有我可以看嗎？**
    - 如果您的 GitHub Repo 是 Public，那任何人擁有網址都可以訪問。
    - 如果需要權限控管，Streamlit Cloud 需付費版或使用其他驗證機制 (但目前我們先求跑起來)。
