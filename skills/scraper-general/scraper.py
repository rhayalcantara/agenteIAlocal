from selenium import webdriver

def scrape(url):
    driver = webdriver.Chrome()
    driver.get(url)
    html = driver.page_source
    driver.quit()
    return html

if __name__ == "__main__":
    import sys
    print(scrape(sys.argv[1]))