# DigitalOcean 部署指南

本指南將協助您將鑑價平台部署到 DigitalOcean Droplet (VPS)。

## 第一步：建立 DigitalOcean Droplet

1.  登入 [DigitalOcean Console](https://cloud.digitalocean.com/)。
2.  點擊右上角 **Create** -> **Droplet**。
3.  **Region**: 選擇離您或使用者最近的資料中心 (例如 **Singapore**)。
4.  **Choose an image**: 選擇 **Marketplace** -> 搜尋 **Docker** -> 選擇 **Docker on Ubuntu** (這會預裝好 Docker，省去安裝步驟)。
5.  **Size**: 
    - 選擇 **Basic**。
    - **CPU options**: Regular with SSD。
    - 價格選擇 **$6/month** (1GB RAM / 1 CPU) 或是 **$4/month** (如果有的話)。對於此應用程式，1GB RAM 通常足夠。
6.  **Authentication Method**: 
    - **Password**: 設定一個強密碼 (這是最簡單的方式)。
    - **SSH Key**: (進階) 建議使用，但若不熟悉可先用密碼。
7.  **Hostname**: 給它一個好記的名字，例如 `car-valuation-app`。
8.  點擊 **Create Droplet**。

等待幾分鐘，Droplet 建立完成後，您會看到它的 **IP Address** (例如 `123.456.78.90`)。

## 第二步：設定部署腳本

我已經準備了一個自動化部署腳本 `vps_deployer.py`。

1.  打開 `vps_deployer.py`。
2.  修改最上方的設定區塊：
    ```python
    # Configuration
    VPS_IP = "您的_DROPLET_IP"
    VPS_USER = "root"
    VPS_PASSWORD = "您的_ROOT_密碼"
    REPO_URL = "您的_GITHUB_REPO_URL" # 例如 https://github.com/Start-0/car-valuation-platform.git
    ```
    *(注意：請確保您的 GitHub Repo 是 Public 的，或者您需要在 VPS 上設定 SSH Key 才能拉取 Private Repo)*

## 第三步：執行部署

在您的電腦上 (VS Code Terminal)：

1.  安裝必要的 Python 套件 (如果您還沒裝 paramiko)：
    ```bash
    pip install paramiko
    ```
2.  執行腳本：
    ```bash
    python vps_deployer.py
    ```

腳本會自動連線到您的 VPS，拉取最新的程式碼，並使用 Docker 啟動應用程式。

## 第四步：訪問應用程式

部署完成後，打開瀏覽器輸入：
`http://<您的_DROPLET_IP>`

您應該就能看到鑑價平台了！

## 常見問題

### 如何更新程式？
1.  在本地修改程式碼並 push 到 GitHub。
2.  再次執行 `python vps_deployer.py`。腳本會自動拉取最新程式碼並重啟服務。

### 遇到 Permission denied (publickey)？
- 檢查 `VPS_PASSWORD` 是否正確。
- 如果您在建立 Droplet 時選擇了 SSH Key，`paramiko` 需要指向您的私鑰路徑 (這需要修改腳本)。建議初學者使用 Password 驗證較簡單。

### 網站打不開？
- 確保 DigitalOcean 防火牆沒有阻擋 port 80。
- 登入 VPS (`ssh root@<IP>`) 並執行 `docker ps` 查看容器是否在執行。
- 執行 `docker logs <容器ID>` 查看錯誤訊息。
