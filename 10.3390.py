import re
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

    for div in soup.find_all('div', class_='html-p'):
        # 检查是否包含特定文本
        if "The following supporting information can be downloaded at:" in div.text:
            # 查找所有链接
            for link in div.find_all('a'):
                href = link.get('href')
                # 只保留以 https://www.mdpi.com 开头的链接
                if href and href.startswith('https://www.mdpi.com'):
                    supporting_info_links.append(href)

    # 去重
    supporting_info_links = list(set(supporting_info_links))

    # 检查支持信息链接是否为空
    if not supporting_info_links:
        print("No downloadable supporting information links found.")
        return False  # 结束函数

    # 如果找到支持信息链接
    success_count = 0  # 记录成功下载的数量
    total_links = len(supporting_info_links)  # 获取链接的总数量

    for supporting_info_link in supporting_info_links:

        # 检查下载链接的重定向
        try:
            # 直接请求支持信息链接
            download_response = session.get(supporting_info_link, headers=headers)
            print(f"Download response status code: {download_response.status_code}")

            # 检查请求是否成功
            download_response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred: {e}")
            continue  # 继续下一个链接
        except requests.exceptions.RequestException as e:
            print(f"Error occurred: {e}")
            continue  # 继续下一个链接

        if download_response.status_code == 200:
            os.makedirs('10.3390_1', exist_ok=True)

            # 生成文件名
            content_disposition = download_response.headers.get('Content-Disposition')
            filename_match = re.findall('filename="(.+?)"', content_disposition)
            filename = filename_match[0]
            file_extension = os.path.splitext(filename)[-1]
            base_name = f"s{success_count}_{SiPDFName[3:]}"

            file_path = os.path.join('10.3390_1', f"{base_name}{file_extension}")

            # 将响应内容写入文件
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
    # 筛选出 DOI 以 "10.3390" 开头的行
    df = raw_df[raw_df['DOI'].str.startswith('10.3390')]
    df.loc[:, 'processed'] = False

    for index, row in df.iterrows():
        doi = row['DOI']
        SiPDFName = row['SiPDFName']

        processed = download_supporting_information(doi, SiPDFName)
        df.at[index, 'processed'] = processed
        time.sleep(10)

        output_file = os.path.join(dir, '10.3390.csv')
        df.to_csv(output_file, index=False)

        print(f"DataFrame saved to {output_file}")