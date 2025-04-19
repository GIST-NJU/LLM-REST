# LLM-REST
  
## 环境准备
注1：所有试验环境均使用Python并使用Anaconda进行环境管理。请查阅` https://www.anaconda.com/download/success `网站以安装适合自己系统的Anaconda。

环境安装命令
``` 
cd LLM-REST
sh setup.sh 
```

这里命令会安装两个工作需要的全部python环境

## Work1:OpenAPI文档分析 
 
### 介绍  
  
这是毕业论文中第一部分工作，用于对于OpenAPI文档进行特征分析。主要代码位于`Analyse`文件夹中。

### 分档分析  

主要内容分为三部分：  
  
1. 从APIs.guru以及SwaggerHub下载OpenAPI文档：  
  
   - ``` conda run -n llm-rest python Analyse/download.py ```  
  
   - APIs.guru下载大约**20分钟**，SwaggerHub下载约需**2小时**。  
  
   - SwaggerHub通过提供的API进行文档获取，但是无法获取全部的文档，在API请求中通过`?limit=100&page={i}&state=PUBLISHED`进行控制，但page参数最大值仅为100，也就是一共可以获取到100x100=10000个OpenAPI文档，但SwaggerHub中有30000+个文档，目前仍无法全部获取，没有找到方法。  
  
2. 对所有的文档进行版本转化以及预处理：
  
   - 将所有V2版本的文档转化为V3版本，以便统一的处理。``` conda run -n llm-rest python Analyse/convert.py ```
   - 将所有文档进行预处理，修改一些不影响分析的错误内容。``` conda run -n llm-rest python Analyse/preprocess.py ```

3. 分析文档并使用CSV文件保存分析结果，用于画图分析。

   - ``` conda run -n llm-rest python Analyse/parse.py ```
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

注：由于网络问题，可能部分文档下载存在问题，导致下载结果有所出入。

### 画图

运行

```conda run -n llm-rest python Analyse/plot.py ```

## Work2:基于大语言模型的 RESTful APIs 测试方法研究

### 介绍

这是毕业论文中第二部分工作，用于基于大语言模型的 RESTful APIs 测试方法研究。主要代码位于`LLMREST_core`文件夹中。

### 运行命令

```
conda run -n llm-rest python LLMREST_core/llm_rest.py \
 --exp_name <exp_name> \
 --spec_file <path to spec file> \
 --budget <time budget> \
 --output_path <path to output folder> \
 --server <server url> \
 --token <token>
```
- `--exp_name`：实验名称
- `--spec_file`：OpenAPI文档路径
- `--budget`：时间预算，单位为秒
- `--output_path`：输出文件夹路径，用于保存LLM调用相关结果
- `--server`：API服务器地址，如 http://localhost:5000. 如果不提供，则从文档推断（**建议提供，因为服务的port存在变化，文档中的port写死**）
- `token`：API服务器的token，如果不需要token，则不提供该参数

有关大语言模型的参数在`LLMREST_core/configs.py`中进行设置，主要包括：
- `api_key`：调用大语言模型的API密钥
- `openai_url`：OpenAI的BaseURL地址，如不提供则默认使用OpenAI自己的网站（需要梯子），鉴于试验考虑，推荐使用国内的中转网站（实验中使用```https://api.bianxieai.com```），无需连接外网即可调用，具体的BaseURL可以在中转网站的教程中获取
- `model`：具体使用的大语言模型
- `temperature`：大语言模型的温度参数

### 实验运行

实验运行需要先启动SUT服务，SUT部署与启动参考GIST-NJU/EmRest ```https://github.com/GIST-NJU/EmRest/tree/master```

其中有完善的脚本以及部署命令，以及结果分析脚本