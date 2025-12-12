# gcloud auth application-default login       # if necessary
# python3 test_cloud.py

# gsutil cat gs://rms-jspitale/test.txt

#from filecache import FCPath
#FCPath('gs://rms-jspitale/test.txt').write_text('Hello\nWorld\n', encoding='utf-8')
#exit()


from filecache import FCPath

#filespec = FCPath('gs://rms-jspitale/test.txt')
filespec = FCPath('gs://rms-jspitale/xxx/yyy/zzz/aaa/bbb/test.txt')
if filespec.exists():
    content = filespec.read_text(encoding='utf-8')
    filespec.write_text(content + '\nGoodbye\nWorld\n', encoding='utf-8')
    exit()

filespec.write_text('Hello\nWorld\n', encoding='utf-8')
exit()



