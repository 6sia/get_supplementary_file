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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    # 发送 GET 请求
    response = session.get(url, headers=headers)

    # 检查请求是否成功
    if response.status_code != 200:
        print(f"Failed to access {url}, status code: {response.status_code}")
        return False

    # 解析 HTML 内容
    raw_soup = BeautifulSoup(response.content, 'html.parser')
    # *******************************
    # 从 HTML 中提取重定向 URL
    redirect_url = None
    for input_tag in raw_soup.find_all('input'):
        if input_tag.get('id') == 'redirectURL':
            redirect_url = input_tag['value']
            break

    if redirect_url is None:
        print("No redirect URL found.")
        return False

    # 重定向到实际的文章页面
    article_url = redirect_url.replace('%3A', ':').replace('%2F', '/').replace('%3F', '?').replace('%3D', '=')
    article_url = article_url.replace('%253D', '=')  # 修正双重编码
    print(f"Redirecting to: {article_url}")

    # 添加 Referer 和 Accept 头
    headers['Referer'] = url
    headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'

    # 请求文章页面
    article_response = session.get(article_url, headers=headers)

    if article_response.status_code != 200:
        print(f"Failed to access the article page, status code: {article_response.status_code}")
        return False

    # 解析文章页面
    soup = BeautifulSoup(article_response.content, 'html.parser')
    # *******************************

    # 查找支持信息链接
    supporting_info_links = []
    supported_formats = ('.pdf', '.doc', '.docx', '.xls', '.xlsx')

    for link in soup.find_all('a', class_='download-link'):
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
            supporting_info_link = f"https://www.sciencedirect.com{supporting_info_link}"

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
            os.makedirs('10.1016', exist_ok=True)

            file_extension = os.path.splitext(supporting_info_link)[-1]
            base_name = SiPDFName if file_extension in ['.doc', '.docx', '.pdf'] else f"s{success_count}_{SiPDFName[3:]}"

            file_path = os.path.join('10.1016', f"{base_name}{file_extension}")

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
    # 筛选出 DOI 以 "10.1016" 开头的行
    df = raw_df[raw_df['DOI'].str.startswith('10.1016')]
    df.loc[:, 'processed'] = False

    doi = '10.1016/j.actbio.2022.11.010'
    SiPDFName = 'si_10.1016_j.actbio.2022.11.010'
    processed = download_supporting_information(doi, SiPDFName)

    for index, row in df.iterrows():
        doi = row['DOI']
        SiPDFName = row['SiPDFName']

        processed = download_supporting_information(doi, SiPDFName)
        df.at[index, 'processed'] = processed
        time.sleep(10)

        output_file = os.path.join(dir, '10.1016_status.csv')
        df.to_csv(output_file, index=False)

        print(f"DataFrame saved to {output_file}")