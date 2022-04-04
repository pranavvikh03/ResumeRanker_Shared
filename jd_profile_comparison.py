from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer
import pickle

class jd_profile_comparison:
    def __init__(self):
        pass

    def __matcher(self,job_desc,resume_text):
        text=[resume_text,job_desc]
        cv=CountVectorizer()
        count_matrix=cv.fit_transform(text)
        matchper=cosine_similarity(count_matrix)[0][1] * 100
        return round(matchper,2)
    
    def match(self,jd,resumetext):
        return self.__matcher(jd,resumetext)

obj_jd_profile_comparison = jd_profile_comparison()
pickle.dump(obj_jd_profile_comparison,open("jd_profile_comparison.pkl","wb"))