import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



# Greenhouse: z.B. Isar Aerospace
def fetch_greenhouse(company_name, api_url):
    resp = requests.get(api_url)
    resp.raise_for_status()
    data = resp.json()
    jobs = []
    for job in data.get("jobs", []):
        title = job.get("title", "")
        if any(k in title for k in ["Working Student", "Werkstudent"]):
            jobs.append((company_name, title, job.get("absolute_url")))
    return jobs

# Personio: z.B. OroraTech
def fetch_personio(company_name, xml_url):
    resp = requests.get(xml_url + "?language=en")
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "xml")
    jobs = []
    for pos in soup.find_all("position"):
        title = pos.find("name").get_text()
        seniority = pos.find("seniority").get_text() if pos.find("seniority") else ""
        if "student" in seniority.lower() or "working student" in title.lower() or "werkstudent" in title.lower():
            job_id = pos.find("id").get_text()
            url = f"https://{company_name.lower()}.jobs.personio.de/job/{job_id}"
            jobs.append((company_name, title, url))
    return jobs

def fetch_mobility_house():
    jobs = []
    try:
        url = "https://www.mobilityhouse.com/de_de/unser-unternehmen/karriere#jobs"
        resp = requests.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        job_links = soup.find_all("a", attrs={"data-cy": "jobOpeningLink"})


        for link in job_links:
            first_div = link.find_all("span", recursive=False)[0]
            title = first_div.get_text(strip=True)
            job_type_span = link.find("span", attrs={"data-cy": "employmentType"})
            job_type = job_type_span.get_text(strip=True) if job_type_span else ""

            if any(kw in title.lower() for kw in ["werkstudent", "working student"]) or \
               "werkstudium" in job_type.lower():
                href = link.get("href")
                full_url = href if href.startswith("http") else f"https://www.mobilityhouse.com{href}"
                jobs.append(("MobilityHouse", title, full_url))

    except Exception as e:
        print(f"The Mobility House scraping failed: {e}")
    return jobs



# BMW: SuccessFactors API (Vorsicht: viele Ergebnisse -> gefiltert nach München + Werkstudent)
def fetch_bmw_selenium():
    jobs = []
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.bmwgroup.jobs/de/en/jobs.html")
        time.sleep(5)

        # Consent-Banner akzeptieren, falls vorhanden
        try:
            time.sleep(3)
            shadow_host = driver.find_element(By.CSS_SELECTOR, "epaas-consent-drawer-shell")
            shadow_root = driver.execute_script("return arguments[0].shadowRoot", shadow_host)
            consent_button = shadow_root.find_element(By.CSS_SELECTOR,
                                                      "body > div > div > section > div.actions > div > div.buttons > button.accept-button.button-primary"
                                                      )
            consent_button.click()
            print("✅ Consent-Banner im Shadow DOM akzeptiert.")
            time.sleep(2)
        except Exception as e:
            print("⚠️ Kein Consent-Banner gefunden oder Fehler beim Klick:", e)

        # Location: Munich
        dropdown_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@title='Location filter']"))
        )
        dropdown_button.click()

        munich_checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "location_DE/Munich"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", munich_checkbox)
        munich_checkbox.click()

        # Publication Date: Last 7 days
        dropdown_button_posting_date = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@title='Publication filter']"))
        )
        dropdown_button_posting_date.click()

        last_7_days_checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "postingDate_7"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", last_7_days_checkbox)
        last_7_days_checkbox.click()

        # Search for Werkstudent
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.grp-text-search"))
        )
        search_input.clear()
        search_input.send_keys("Werkstudent")

        search_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.grp-text-search-icon"))
        )
        search_button.click()

        # Iterate through pages
        while True:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "grp-jobfinder__cell-title"))
            )

            job_elements = driver.find_elements(By.CLASS_NAME, "grp-jobfinder__cell-title")
            links = driver.find_elements(By.CLASS_NAME, "grp-popup-link-js.grp-jobfinder__link-jobdescription")

            for i in range(len(job_elements)):
                title = job_elements[i].text
                href = links[i].get_attribute("href")
                jobs.append(("BMW", title, href))

            # Nächste Seite prüfen
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "button.grp-jobfinder__pagination-button.next")
                if "disabled" in next_button.get_attribute("class"):
                    break
                next_button.click()
                time.sleep(4)
            except:
                break

        driver.quit()
    except Exception as e:
        print(f"BMW Selenium scraping failed: {e}")
    return jobs



if __name__ == "__main__":
    results = []
    results += fetch_greenhouse("Isar Aerospace", "https://boards-api.greenhouse.io/v1/boards/isaraerospace/jobs")
    results += fetch_personio("OroraTech", "https://ororatech.jobs.personio.de/xml")
    results += fetch_personio("GridX", "https://gridx.jobs.personio.de/xml")
    #results += fetch_personio("AgileRobots", "https://agilerobots.jobs.personio.de/xml")
    results += fetch_mobility_house()
    results += fetch_bmw_selenium()

    if results:
        print("🎓 Aktuelle Werkstudentenstellen:\n")
        for comp, title, url in results:
            print(f"[{comp}] {title}\n{url}\n")
    else:
        print("🚫 Keine Werkstudent*innen-Stellen gefunden.")
