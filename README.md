## CS 203 Lab Assignment 1

#### Data Collection using OpenTelemetry and Jaeger

---

**_Team Members_**
Name | Roll Number
---|---
Soham Gaonkar| 23110314
Chaitanya Sharma | 23110072

---

#### Features 

---

### 1. Logging and Tracing of Page Visits

- **Screenshot 1 , 2:** Homepage and Course Catalog page.  
  ![Homepage ](CS203_Lab_01/screenshots/1.png)
  ![Catalog Page with Add Button](CS203_Lab_01/screenshots/2.png) 

- **Screenshot 3:** .Tarce Collected on Jaeger of homepage and course catalog visit.  
  ![Jaeger UI](CS203_Lab_01/screenshots/3.png)

- **Screenshot 4:**  Viewing Course Details.  
  ![Course Details](CS203_Lab_01/screenshots/4.png)

- **Screenshot 5:**  Trace Collected on Jaeger of course page visit.  
  ![Jaeger UI](CS203_Lab_01/screenshots/5.png)

### 2. Adding Courses 

- **Screenshot 6:** Incomplete Form Submission.  
  ![Add Course](CS203_Lab_01/screenshots/6.png)

- **Screenshot 7 , 8 , 9:** Confirmation message after successfully adding a course. 
  ![Form Submission](CS203_Lab_01/screenshots/7.png) 
  ![Confirmation Message](CS203_Lab_01/screenshots/8.png)  
  ![Viewing Added Course](CS203_Lab_01/screenshots/9.png)

- **Screenshot 10:** Log of successful course addition.  
  ![Log](CS203_Lab_01/screenshots/9.5.png)

---

### 2. Invalid Page Requests and Error Handling

- **Screenshot 10:** Invalid Course ID.  
  ![Invalid Course ID](CS203_Lab_01/screenshots/10.png)

- **Screenshot 11:** Tracing data for invalid course request.  
  ![Invalid course Trace](CS203_Lab_01/screenshots/11.png)
  ![Invalid course Trace](CS203_Lab_01/screenshots/12.png)

- **Screenshot 12:** Invalid Page Handling. 
  ![Invalid Page Handling](CS203_Lab_01/screenshots/13.png)
  ![Invalid Page Handling](CS203_Lab_01/screenshots/14.png)

- **Screenshot 13:** Structurred Logs saved in JSON format.  
  ![JSON Logs](CS203_Lab_01/screenshots/15.png)
-
---

### 3. Metrics Data

- **Screenshot 14:** Total number of requests made to each endpoint.  
  ![Metrics](CS203_Lab_01/screenshots/16.png)

- **Screenshot 15:** Processing time for each endpoint.  
  ![Metrics](CS203_Lab_01/screenshots/17.png)

- **Screenshot 16:** Error Count for each endpoint.  
  ![Metrics](CS203_Lab_01/screenshots/18.png)



---

Dependencies:
- `flask`, `opentelemetry-instrumentation`, `opentelemetry-instrumentation-flask`, `opentelemetry-exporter-jaeger`

To run the project:
- Run `python app.py` in the terminal.

---