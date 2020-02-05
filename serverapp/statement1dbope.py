from pymongo import MongoClient
from pprint import pprint

db = MongoClient()
mydb = db.dhi_analytics
dhi_internal = mydb['dhi_internal']
dhi_term_details = mydb['dhi_term_detail']
dhi_student_attendance = mydb['dhi_student_attendance']


def getacademicYear():
    academicYear = dhi_internal.aggregate([{"$group":{"_id":"null",
    "academicYear":{"$addToSet":"$academicYear"}}},{"$project":{"academicYear":"$academicYear","_id":0}}])
    for year in academicYear:
        year = year['academicYear']
    return year

def get_term_numbers():
    terms_numbers = dhi_term_details.aggregate([ 
        { "$unwind":"$academicCalendar"}, 
        {"$group":{"_id":"null","termNumber":{"$addToSet":"$academicCalendar.termNumber"}}},
        {"$project":{"_id":0}}
    ])
    for term in terms_numbers:
        terms = term['termNumber']
    terms.sort()
    return terms



def get_ia_details(usn,courseCode,section,termNumber,deptId,year):
    ia_percent = 0
    avg_ia_score = 0

    ia_details =[x for x in dhi_internal.aggregate([
        {
        '$unwind': '$studentScores'
        },
        {'$unwind': '$departments'},
        {'$unwind':'$studentScores.evaluationParameterScore'},
        {
            '$match':
            {
                'studentScores.usn':usn,
                'academicYear':year,
                'courseCode':courseCode ,
                'studentScores.section': section,
                'departments.deptId': deptId,
                'studentScores.termNumber': termNumber
            }
        
        },

        {
            '$group':
            {
                '_id':'$iaNumber',
                "maxMarks":{"$addToSet":"$studentScores.evaluationParameterScore.maxMarks"},
                "iaNumber":{"$addToSet":"$iaNumber"},
                "obtainedMarks":{"$addToSet":"$studentScores.totalScore"},
                "startTime":{"$addToSet":"$startTime"}
            }
        },
        {'$unwind':'$maxMarks'},
        {'$unwind':'$iaNumber'},
        {'$unwind':'$startTime'},
        {'$unwind':'$obtainedMarks'},
        {
            "$project":
                {
                    "_id":0,
                    "maxMarks":"$maxMarks",
                    "obtainedMarks":"$obtainedMarks",
                    "startTime":"$startTime",
                    "iaNumber":"$iaNumber"
                }
        }

    ])]
    for x in ia_details:
        try:
            ia_percent = (x['obtainedMarks']/x['maxMarks'])*100
            ia_percent =  round(ia_percent,2)
            x['ia_percent'] = ia_percent
            avg_ia_score = avg_ia_score + ia_percent
        except ZeroDivisionError:
            avg_ia_score = 0
    
    try:
        avg_ia_score = avg_ia_score/len(ia_details)
        avg_ia_score = round(avg_ia_score,2)
        return ia_details,avg_ia_score
    except ZeroDivisionError:
        return ia_details,0



def get_avg_attendance(usn,courseCode,section,termNumber,deptId,year):

    for attedance_details in dhi_student_attendance.aggregate([
        {'$unwind': '$departments'},
        {'$unwind':'$students'},
        
    
        {
            '$match':
                    {
                    'academicYear':year,
                    'students.usn':usn,
                    'courseCode': courseCode,
                    'students.deptId': deptId,
                    'students.section':section,
                    'students.termNumber':termNumber
                    }
        },
      
        {
            '$project':
                    {
                        '_id':0,
                        'totalNumberOfClasses':'$students.totalNumberOfClasses',
                        'totalPresent':'$students.presentCount',
                        'totalAbsent':'$students.absentCount'
                    }
        }
 
    ]):
        attendance_per = (attedance_details['totalPresent']/attedance_details['totalNumberOfClasses'])*100
        attendance_per = round(attendance_per,2)
        attendance = {"attedance_details":attedance_details,"attendance_per":attendance_per}
        return attendance



def get_iadate_wise_attendance(usn,courseCode,section,termNumber,deptId,year,iadate,iaNumber):
    present_details = []
    present = []
    absent = []
    perc_of_present = 0
    perc_of_absent = 0 
    for x in dhi_student_attendance.aggregate([
        {'$unwind': '$departments'},
        {'$unwind':'$students'},
        {
            '$match':
                    {
                    'academicYear':year,
                    'students.usn':usn,
                    'courseCode': courseCode,
                    'students.deptId': deptId,
                    'students.section':section,
                    'students.termNumber':termNumber
                    }
        },
        {'$unwind':'$students.studentAttendance'},
        { 
            '$match': 
            {
                "students.studentAttendance.date":{"$lte":iadate}
            }   
        },      
        {
            '$project':
                    {
                        "_id":0,
                        "date":"$students.studentAttendance.date",
                        "present":"$students.studentAttendance.present"
                    }
        }
 
    ]):
        present_details.append(x['present'])
        if x['present'] == True:
            present.append(x['present'])
        if x['present'] == False:
            absent.append(x['present'])
    try:
        perc_of_present = (len(present)/len(present_details))*100
        perc_of_present = round(perc_of_present,2)
        perc_of_absent = (len(absent)/len(present_details))*100
        perc_of_absent = round(perc_of_absent,2)
    except:
        perc_of_present = 0 
        perc_of_absent = 0

    return perc_of_present,perc_of_absent


def get_details(usn,year,terms):   
    final_attendance = []

    for x in dhi_internal.aggregate([
        {'$unwind':'$studentScores'},
        {'$unwind':'$departments'},
        {
        '$match':
        {
            'studentScores.usn':usn,
            'academicYear': year,
            'departments.termNumber': {'$in':terms}
        }
        },
        {
            '$group':
            {
                '_id':
                {
                    'courseCode': '$courseCode',
                    'courseName': '$courseName',
                    'section': '$studentScores.section',
                    'termNumber': '$studentScores.termNumber',
                    'deptId': '$departments.deptId'
                }   
            }
        }
    ]):
        details = {}
        ia_details,avg_ia_score = get_ia_details(usn,x['_id']['courseCode'],x["_id"]
                                ["section"],x["_id"]["termNumber"], x["_id"]["deptId"],year)
        attedance_total_avg_details = get_avg_attendance(usn,x['_id']['courseCode'],x["_id"]
                                ["section"],x["_id"]["termNumber"], x["_id"]["deptId"],year)
        for ia_detail in ia_details:
            try:
                ia_detail['perc_of_present'],ia_detail['perc_of_absent'] = get_iadate_wise_attendance(usn,x['_id']['courseCode'],x["_id"]
                                    ["section"],x["_id"]["termNumber"], x["_id"]["deptId"],year,ia_detail['startTime'],ia_detail['iaNumber'])
            except KeyError:
                ia_detail['perc_of_present'] = 0 
                ia_detail['perc_of_absent'] = 0
        details['total_avg'] = {}
        details['attendance_per'] = 0
        details['courseCode'] = x['_id']['courseCode']
        details['courseName'] = x['_id']['courseName']
        details['section'] = x['_id']['section']
        details['termNumber'] = x['_id']['termNumber']
        details['deptId'] = x['_id']['deptId']
        details['ia_attendance_%'] = ia_details
        details['avg_ia_score'] = avg_ia_score
        if attedance_total_avg_details != None:
            details['total_avg'] = attedance_total_avg_details['attedance_details']
            details['attendance_per'] = attedance_total_avg_details['attendance_per']
        final_attendance.append(details)
    return final_attendance
# get_details('4MT16CV004','2017-18',['1','2','3','4','5','6','7','8'])
