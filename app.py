from flask import Flask, render_template, url_for, request, session, redirect, abort, jsonify
from database import mongo
from werkzeug.utils import secure_filename
import os
import pickle
from resumeExtraction import resumeExtraction
import sys,fitz
from resumeScreener import resumeScreener
from bson.objectid import ObjectId
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
import pathlib
import requests




def allowedExtension(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ['docx','pdf']

app = Flask(__name__)


app.secret_key = "Resume_screening"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
GOOGLE_CLIENT_ID = #Enter your google client id here
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json") #Enter your updated client_secret.json data
flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)






UPLOAD_FOLDER = 'static/resumes'
app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER
app.config['MONGO_URI']=#Enter mongo db uri here
mongo.init_app(app)
resumeFetchedData = mongo.db.resumeFetchedData
Ranked_resume = mongo.db.Ranked_resume
IRS_USERS = mongo.db.IRS_USERS
JOBS = mongo.db.JOBS
from Job_post import job_post
app.register_blueprint(job_post,url_prefix="/HR1")
extractorObj = pickle.load(open("resumeExtractor.pkl","rb"))
screenerObj = pickle.load(open("resumeScreener.pkl","rb"))

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/emp')
def emp():
    if 'user_id' in session and 'user_name' in session:
        return render_template("EmployeeDashboard.html")
    else:
        return render_template("index.html", errMsg="Login First")

@app.route('/login')
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )
    result = None
    result = IRS_USERS.find_one({"Email":id_info.get("email")},{"_id":1})
    if result == None:
        session['user_id'] = str(IRS_USERS.insert_one({"Name":id_info.get("name"),"Email":id_info.get("email"),"Google_id":id_info.get("sub")}).inserted_id)
        session['user_name'] = str(id_info.get("name"))
    else:
        session['user_id'] = str(result['_id'])
        session['user_name'] = str(id_info.get("name"))
    return redirect("/emp")



@app.route('/signup', methods=["POST"])
def signup():
    if request.method == 'POST':
        name = str(request.form.get('name'))
        email = str(request.form.get('email'))
        password = str(request.form.get('password'))
        status = None
        status = IRS_USERS.insert_one({"Name":name,"Email":email,"Password":password})
        if status == None:
            return render_template("index.html",errMsg="Problem in user creation check data or try after some time")
        else:
            return render_template("index.html",successMsg="User Created Successfully!")

@app.route("/logout")
def logout():
    session.pop('user_id',None)
    session.pop('user_name',None)
    return redirect(url_for("index"))

@app.route('/HR')
def HR():
    return render_template("CompanyDashboard.html")


@app.route('/test')
def test():
    return "Connection Successful"

@app.route("/uploadResume", methods=['POST'])
def uploadResume():
    if 'user_id' in session and 'user_name' in session:
        try:
            file = request.files['resume']
            filename = secure_filename(file.filename)
            print("Extension:",file.filename.rsplit('.',1)[1].lower())
            if file and allowedExtension(file.filename):
                temp = resumeFetchedData.find_one({"UserId":ObjectId(session['user_id'])},{"ResumeTitle":1})
                if temp == None:
                    print("HELLO")
                else:
                    print("hello")
                    resumeFetchedData.delete_one({"UserId":ObjectId(session['user_id'])})
                    Ranked_resume.delete_one({"UserId":ObjectId(session['user_id'])})
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'],temp['ResumeTitle']))
                file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
                fetchedData=extractorObj.extractorData("static/resumes/"+filename,file.filename.rsplit('.',1)[1].lower())
                skillsPercentage = screenerObj.screenResume(fetchedData[5])
                result = result1 = None
                print("FetchedData:",fetchedData)
                result = resumeFetchedData.insert_one({"UserId":ObjectId(session['user_id']),"Name":fetchedData[0],"Mobile_no":fetchedData[1],"Email":fetchedData[2],"Skills":list(fetchedData[3]),"Education":fetchedData[4],"Appear":0,"ResumeTitle":filename,"ResumeData":fetchedData[5]})                
                if result == None:
                    return render_template("EmployeeDashboard.html",errorMsg="Problem in Resume Data Storage")  
                else:
                        result1 = Ranked_resume.insert_one({"UserId":ObjectId(session['user_id']),"Top_skills":dict(skillsPercentage)})
                        if result1 == None:
                            return render_template("EmployeeDashboard.html",errorMsg="Problem in Skills Data Storage")
                        else:
                            return render_template("EmployeeDashboard.html",successMsg="Resume Screen Successfully!!")
            else:
                return render_template("EmployeeDashboard.html",errorMsg="Document Type Not Allowed")
        except:
            print("Exception Occured")
    else:
        return render_template("index.html", errMsg="Login First")

@app.route('/viewdetails', methods=['POST', 'GET'])
def viewdetails():      
    employee_id = request.form['employee_id']     
    result = resumeFetchedData.find({"UserId":ObjectId(employee_id)})     
    dt=result[0]  
    name=dt['Name']
    email=dt['Email']
    mobile=dt['Mobile_no']
    skills=dt['Skills']
    education=dt['Education']    
    return jsonify({'name':name,'email':email,'mobile':mobile,'skills':skills,'education':education})

@app.route("/empSearch",methods=['POST'])
def empSearch():
    if request.method == 'POST':
        category = str(request.form.get('category'))
        TopEmployeers=None
        TopEmployeers=Ranked_resume.find({"Top_skills."+category:{"$ne":None}},{"Top_skills."+category:1,"UserId":1}).sort([("Top_skills."+category,-1)])
        if TopEmployeers == None:
            return render_template("CompanyDashboard.html",errorMsg="Problem in Category Fetched")
        else:
            selectedResumes={}
            cnt = 0

            for i in TopEmployeers:
                se=IRS_USERS.find_one({"_id":ObjectId(i['UserId'])},{"Name":1,"Email":1,"_id":1})
                selectedResumes[cnt] = {"Name":se['Name'],"Email":se['Email'],"_id":se['_id']}
                se = None
                cnt += 1
            return render_template("CompanyDashboard.html",len = len(selectedResumes), data = selectedResumes)

if __name__=="__main__":
    app.run(debug=True)