import spacy
from spacy.matcher import Matcher
import re
import pandas as pd
import sys, fitz
import nltk
#nltk.download('stopwords')
from nltk.corpus import stopwords
import pymongo
from pymongo import MongoClient
import os
import docx2txt
import pickle
from nltk.tokenize import word_tokenize

class resumeExtraction:
    def __init__(self):
        self.STOPWORDS = set(stopwords.words('english')+['``',"''"])
        # Education Degrees
        self.EDUCATION = [
                    'BE', 'BSC', 'BS', 
                    'ME','MS','BCOM','BCS','BCA','MCA',
                    'BTECH', 'MTECH','DIPLOMA','12TH','10TH',
                    'SSC', 'HSC', 'CBSE', 'ICSE', 'X', 'XII', 'XTH','XIITH','FE','SE','TE'
                ]
        self.data= pd.read_csv("assets/data/newskill2.csv") 
        self.SKILLS_DB = list(self.data.columns.values)
        self.nlp = spacy.load('en_core_web_sm')
        self.matcher = Matcher(self.nlp.vocab)
    
    def __clean_text(self,resume_text):
        resume_text = re.sub('http\S+\s*', ' ', resume_text)  # remove URLs
        resume_text = re.sub('RT|cc', ' ', resume_text)  # remove RT and cc
        resume_text = re.sub('#\S+', '', resume_text)  # remove hashtags
        resume_text = re.sub('@\S+', '  ', resume_text)  # remove mentions
        resume_text = re.sub('[%s]' % re.escape("""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""), ' ', resume_text)  # remove punctuations
        resume_text = re.sub(r'[^\x00-\x7f]',r' ', resume_text) 
        resume_text = re.sub('\s+', ' ', resume_text)  # remove extra whitespace
        resume_text = resume_text.lower()  # convert to lowercase
        resume_text_tokens = word_tokenize(resume_text)  # tokenize
        filtered_text = [w for w in resume_text_tokens if not w in self.STOPWORDS]  # remove stopwords
        return ' '.join(filtered_text)
       
    def __extract_name(self,resume_text):
        nlp_text = self.nlp(resume_text)
        pattern = [{'POS': 'PROPN'}, {'POS': 'PROPN'}]
        
        self.matcher.add('NAME',[pattern])
        
        matches = self.matcher(nlp_text)
        for match_id, start, end in matches:
            span = nlp_text[start:end+1]
            return span.text
    
    def __extract_mobile_number(self,text):
        phone = re.findall(re.compile(r'(?:(?:\+?([1-9]|[0-9][0-9]|[0-9][0-9][0-9])\s*(?:[.-]\s*)?)?(?:\(\s*([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9])\s*\)|([0-9][1-9]|[0-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9]))\s*(?:[.-]\s*)?)?([2-9]1[02-9]|[2-9][02-9]1|[2-9][02-9]{2})\s*(?:[.-]\s*)?([0-9]{4})(?:\s*(?:#|x\.?|ext\.?|extension)\s*(\d+))?'), text)
        if phone:
            number = ''.join(phone[0])
            if len(number) > 10:
                return '+' + number
            else:
                return number
    
    def __extract_email(self,email):
        email = re.findall("([^@|\s]+@[^@]+\.[^@|\s]+)", email)
        if email:
            try:
                return email[0].split()[0].strip(';')
            except IndexError:
                return None
    
    def __extract_education(self,resume_text):
        nlp_text = self.nlp(resume_text)
        
        # Sentence Tokenizer
        nlp_text = [str(sent).strip() for sent in nlp_text.sents]
        edu = {}
        # Extract education degree
        for index, text in enumerate(nlp_text):
            for tex in text.split():
                # Replace all special symbols
                tex = re.sub(r'[?|$|.|!|,|(|)]', r'', tex)
                if tex.upper() in self.EDUCATION and tex not in self.STOPWORDS:
                    edu[tex] = text + nlp_text[index + 1]
                
        # Extract year
        education = []
        for key in edu.keys():
            year = re.search(re.compile(r'(((20|19)(\d{2})))'), edu[key])
            if year:
                education.append((key, ''.join(year[0])))
            else:
                education.append(key)
        return education
    
    def __extract_skills(self,input_text):
        stop_words = set(nltk.corpus.stopwords.words('english'))
        word_tokens = nltk.tokenize.word_tokenize(input_text)

        # remove the stop words
        filtered_tokens = [w for w in word_tokens if w not in stop_words]

        # remove the punctuation
        filtered_tokens = [w for w in word_tokens if w.isalpha()]

        # generate bigrams and trigrams (such as artificial intelligence)
        bigrams_trigrams = list(map(' '.join, nltk.everygrams(filtered_tokens, 2, 3)))

        # we create a set to keep the results in.
        found_skills = set()

        # we search for each token in our skills database
        for token in filtered_tokens:
            if token.lower() in self.SKILLS_DB:
                found_skills.add(token)

        # we search for each bigram and trigram in our skills database
        for ngram in bigrams_trigrams:
            if ngram.lower() in self.SKILLS_DB:
                found_skills.add(ngram)

        return found_skills
    
    def extractorData(self,file,ext): #
        text=""
        if ext=="docx": 
            temp = docx2txt.process(file)
            text = [line.replace('\t', ' ') for line in temp.split('\n') if line]
            text = ' '.join(text)
        if ext=="pdf":
            for page in fitz.open(file):
                text = text + str(page.getText())
            text = " ".join(text.split('\n'))
        #text = self.__clean_text(text)
        text1=text
        name = self.__extract_name(text)
        mobile_no = self.__extract_mobile_number(text)
        email = self.__extract_email(text)
        skills = self.__extract_skills(text)
        education1 = self.__extract_education(text)
        return (name,mobile_no,email,skills,education1,text1)

resumeExtractor = resumeExtraction()

#print(resumeExtractor.extractorData(fitz.open('/home/pranav/Resumes/Pranav Vikharankar.pdf'),"pdf"))
pickle.dump(resumeExtractor,open("resumeExtractor.pkl","wb"))
