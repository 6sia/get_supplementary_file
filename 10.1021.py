import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os


def download_supporting_information(doi, SiPDFName):
    # 创建会话对象
    session = requests.Session()

    # 清除 Cookie
    session.cookies.clear()  # 尝试删除 Cookie

    # 构造请求的 URL
    url = f"https://doi.org/{doi}"

    # 添加请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # 发送 GET 请求
    response = session.get(url, headers=headers)

    # 检查请求是否成功
    if response.status_code != 200:
        print(f"Failed to access {url}, status code: {response.status_code}")
        return False

    # 解析 HTML 内容
    soup = BeautifulSoup(response.content, 'html.parser')

    # 查找支持信息链接
    supporting_info_links = []
    supported_formats = ('.pdf', '.doc', '.docx', '.xls', '.xlsx')

    for link in soup.find_all('a', class_='suppl-anchor'):
        href = link.get('href')
        if href and href.endswith(supported_formats):
            supporting_info_links.append(href)

    # 去重
    supporting_info_links = list(set(supporting_info_links))

    # 检查支持信息链接是否为空
    if not supporting_info_links:
        print("No downloadable supporting information links found.")
        return False  # 结束函数

    # 如果找到支持信息链接
    success_count = 0  # 记录成功下载的数量
    total_links = len(supporting_info_links)  # 获取链接的总数量，除以 2

    for supporting_info_link in supporting_info_links:
        if supporting_info_link.startswith('/'):
            supporting_info_link = f"https://pubs.acs.org{supporting_info_link}"

        # 检查下载链接的重定向
        try:
            download_response = session.get(supporting_info_link, headers=headers, allow_redirects=False)
            print(f"Initial download response status code: {download_response.status_code}")

            # 处理重定向
            if download_response.status_code in (301, 302):
                redirect_url = download_response.headers.get('Location')
                print(f"Redirected to: {redirect_url}")
                download_response = session.get(redirect_url, headers=headers)

            download_response.raise_for_status()  # 检查请求是否成功
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred: {e}")
            continue  # 继续下一个链接
        except requests.exceptions.RequestException as e:
            print(f"Error occurred: {e}")
            continue  # 继续下一个链接

        if download_response.status_code == 200:
            os.makedirs('supporting_information', exist_ok=True)

            file_extension = os.path.splitext(supporting_info_link)[-1]
            base_name = f"s{success_count}_{SiPDFName[3:]}"

            file_path = os.path.join('supporting_information', f"{base_name}{file_extension}")

            with open(file_path, 'wb') as file:
                file.write(download_response.content)
            success_count += 1  # 增加成功下载的计数
            print(f"Downloaded: {file_path}")
        else:
            print(
                f"Failed to download supporting information from {supporting_info_link}, status code: {download_response.status_code}")

    # 最终成功判断
    if success_count == total_links:
        return True  # 所有链接成功下载
    else:
        print(f"Downloaded {success_count} out of {total_links} files.")
        return False  # 不是所有链接都成功下载

if __name__ == "__main__":
    dir = '...'
    file_path = os.path.join(dir, 'si_files - 1.xlsx')

    raw_df = pd.read_excel(file_path, sheet_name='Sheet1')
    # 筛选出 DOI 以 "10.1021" 开头的行
    df = raw_df[raw_df['DOI'].str.startswith('10.1021')]
    df.loc[:, 'processed'] = False

    # doi = '10.1021/nn406018q'
    # SiPDFName = 'si_10.1021_nn406018q'
    # processed = download_supporting_information(doi, SiPDFName)

    for index, row in df.iterrows():
        doi = row['DOI']
        SiPDFName = row['SiPDFName']

        processed = download_supporting_information(doi, SiPDFName)
        df.at[index, 'processed'] = processed
        time.sleep(10)

        output_file = os.path.join(dir, 'supporting_information_status.csv')
        df.to_csv(output_file, index=False)

        print(f"DataFrame saved to {output_file}")