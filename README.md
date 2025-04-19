# LLM-REST
  
## 环境准备
注：所有试验环境均使用Python并使用Anaconda进行环境管理。请查阅` https://www.anaconda.com/download/success `网站以安装适合自己系统的Anaconda。
安装命令
``` 
cd LLM-REST
sh setup.sh 
```
切换到LLM-REST文件夹中或者直接使用LLM-REST文件夹中的setup.sh的绝对路径。

## Work1:OpenAPI文档分析 
 
### 介绍  
  
这是毕业论文中第一部分工作用于对于OpenAPI文档进行特征分析。主要代码位于Analyse文件夹中。

### 分档分析  

主要内容分为三部分：  
  
1. 从APIs.guru以及SwaggerHub下载OpenAPI文档：  
  
   - ``` python Analyse/download.py ```  
  
   - APIs.guru下载大约**20分钟**，SwaggerHub下载约需**2小时**。  
  
   - SwaggerHub通过提供的API进行文档获取，但是无法获取全部的文档，在API请求中通过`?limit=100&page={i}&state=PUBLISHED`进行控制，但page参数最大值仅为100，也就是一共可以获取到100x100=10000个OpenAPI文档，但SwaggerHub中有30000+个文档，目前仍无法全部获取，没有找到方法。  
  
2. 对所有的文档进行版本转化以及预处理：
  
   - 将所有V2版本的文档转化为V3版本，以便统一的处理。``` python Analyse/convert.py ```
   - 将所有文档进行预处理，修改一些不影响分析的错误内容。``` python Analyse/preprocess.py ```

3. 分析文档并使用CSV文件保存分析结果，用于画图分析。

   - ``` python Analyse/parse.py ```
   - 分析结果保存在`Analyse/data`文件夹中，文件结构如下：
```
result_dir/  
├── tools/               
│   ├── structure_info.csv    # 操作指标
│   ├── data_model_info.csv   # 模式指标 
│   ├── nlp_info.csv          # 自然语言指标  
│   └── obey_info.csv         # 文档质量指标        
├── guru/                
│   ├── structure_info.csv    
│   ├── data_model_info.csv  
│   ├── nlp_info.csv          
│   └── obey_info.csv         
├── swaggerhub/            
│   ├── structure_info.csv   
│   ├── data_model_info.csv   
│   ├── nlp_info.csv           
│   └── obey_info.csv       
```
一共有3个文件夹，分别是所有黑盒测试工具使用的文档结果，APIs.guru的结果以及SwaggerHub的结果。每个文件夹中有4个CSV文件，分别对应操作指标、模式指标、自然语言指标和文档质量指标。

已经给出分析的结果用于画图

注：由于网络问题，可能部分文档下载存在问题，导致下载结果有所出入。

### 画图
运行
```python Analyse/plot.py ```
利用分析结果CSV画图