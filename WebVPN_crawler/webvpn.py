from selenium.webdriver.remote.webdriver import WebDriver as wd
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait as wdw
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains as AC
import selenium
import json
from bs4 import BeautifulSoup as BS
import time

class WebVPN:
    def __init__(self, opt: dict, headless=False):
        self.root_handle = None
        self.driver: wd = None
        self.passwd = opt["username"]
        self.userid = opt["password"]
        self.headless = headless

    def login_webvpn(self):
        """
        Log in to WebVPN with the account specified in `self.userid` and `self.passwd`

        :return:
        """
        d = self.driver
        if d is not None:
            d.close()
        d = selenium.webdriver.Chrome()
        d.get("https://webvpn.tsinghua.edu.cn/login")
        username = d.find_elements(By.XPATH,
                                   '//div[@class="login-form-item"]//input'
                                   )[0]
        password = d.find_elements(By.XPATH,
                                   '//div[@class="login-form-item password-field" and not(@id="captcha-wrap")]//input'
                                   )[0]
        username.send_keys(str(self.userid))
        password.send_keys(self.passwd)
        d.find_element(By.ID, "login").click()
        self.root_handle = d.current_window_handle
        self.driver = d
        return d

    def access(self, url_input):
        """
        Jump to the target URL in WebVPN

        :param url_input: target URL
        :return:
        """
        d = self.driver
        url = By.ID, "quick-access-input"
        btn = By.ID, "go"
        wdw(d, 5).until(EC.visibility_of_element_located(url))
        actions = AC(d)
        actions.move_to_element(d.find_element(*url))
        actions.click()
        actions.\
            key_down(Keys.CONTROL).\
            send_keys("A").\
            key_up(Keys.CONTROL).\
            send_keys(Keys.DELETE).\
            perform()

        d.find_element(*url)
        d.find_element(*url).send_keys(url_input)
        d.find_element(*btn).click()

    def switch_another(self):
        """
        If there are only 2 windows handles, switch to the other one

        :return:
        """
        d = self.driver
        assert len(d.window_handles) == 2
        wdw(d, 5).until(EC.number_of_windows_to_be(2))
        for window_handle in d.window_handles:
            if window_handle != d.current_window_handle:
                d.switch_to.window(window_handle)
                return

    def to_root(self):
        """
        Switch to the home page of WebVPN

        :return:
        """
        self.driver.switch_to.window(self.root_handle)

    def close_all(self):
        """
        Close all window handles

        :return:
        """
        while True:
            try:
                l = len(self.driver.window_handles)
                if l == 0:
                    break
            except selenium.common.exceptions.InvalidSessionIdException:
                return
            self.driver.switch_to.window(self.driver.window_handles[0])
            self.driver.close()

    def login_info(self):
        """
        TODO: After successfully logged into WebVPN, login to info.tsinghua.edu.cn

        :return:
        """
        url = "info.tsinghua.edu.cn"
        self.access(url)
        self.switch_another()
        d = self.driver
        username = d.find_elements(By.XPATH,
                                   '//input[@name="userName"]'
                                   )[0]
        password = d.find_elements(By.XPATH,
                                   '//input[@name="password"]'
                                   )[0]
        username.send_keys(str(self.userid))
        password.send_keys(self.passwd + "\n")
        self.driver = d
        try:
            wdw(self.driver, 10).until(EC.visibility_of_element_located([By.ID, "userXm"]))
        except Exception as e:
            print(e)
            raise NotImplementedError

        # Hint: - Use `access` method to jump to info.tsinghua.edu.cn
        #       - Use `switch_another` method to change the window handle
        #       - Wait until the elements are ready, then preform your actions
        #       - Before return, make sure that you have logged in successfully

    def get_grades(self):
        """
        TODO: Get and calculate the GPA for each semester.

        Example return / print:
            2020-秋: *.**
            2021-春: *.**
            2021-夏: *.**
            2021-秋: *.**
            2022-春: *.**

        :return:
        """

        self.switch_another()

        self.access("zhjw.cic.tsinghua.edu.cn/cj.cjCjbAll.do?m=bks_cjdcx&cjdlx=zw")

        for each in self.driver.window_handles:
            self.driver.switch_to.window(each)
            ele = self.driver.find_element(By.XPATH, "/html")
            soup = BS(ele.get_attribute("innerHTML"), "html.parser")
            if soup.title.text == "清华大学学生课程学习记录表":
                break
        else:
            raise RuntimeError("114514")

        result = BS(str(soup.find_all("tbody")[3]), "html.parser").find_all("tr")[1:]

        total_gpa = dict()
        total_credit = dict()
        ret = dict()

        for each in result:
            course = BS(str(each), "html.parser").find_all("td")
            course_info = [str(course[0].text), str(course[4].text), str(course[5].text)]

            for i in range(len(course_info)):
                course_info[i] = course_info[i].replace("\n", " ").replace("\r", " ").replace("\t", " ").replace(" ",
                                                                                                                 "")

            if course_info[1] == 'N/A':
                continue

            credit = int(course_info[0]) % 10
            gpa = float(course_info[1])
            sem = course_info[2]

            if sem in total_gpa.keys():
                total_gpa[sem] = total_gpa[sem] + gpa * credit
                total_credit[sem] = total_credit[sem] + credit
            else:
                total_gpa[sem] = gpa * credit
                total_credit[sem] = credit

        for key in total_gpa.keys():
            ret[key] = total_gpa[key] / total_credit[key]

        return ret


if __name__ == "__main__":
    file = open("./settings.json")
    dc = json.load(file)
    vpn = WebVPN(opt=dc)
    vpn.login_webvpn()
    vpn.login_info()
    grades = vpn.get_grades()
    print(grades)
    target_json = open("./grades.json", encoding='utf8')
    json.dump(grades, target_json, indent=4)
