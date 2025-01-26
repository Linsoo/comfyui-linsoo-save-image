# ComfyUI-Linsoo-Custom-Nodes
별 다른 큰 기능은 없고 개인적으로 필요한 기능을 추가한 노드입니다.<br>
대부분의 테스트는 Comfy 기본 노드들로 구성된 workflow에서 테스트 됐습니다. (커스텀 노드 사용시  제대로 작동 안할 수 있습니다.)
<br>

## 1. 필요 라이브러리
```console
pillow, piexif
```
<br>

## 2. 설치방법.
설치하려면 다음과 같이 이 저장소를 ComfyUI/custom_nodes 폴더로 복제합니다.

```console
git clone https://github.com/Linsoo/ComfyUI-Linsoo-Custom-Nodes.git
```


ComfyUI-Manager 등록은 조금 뒤로 미룹니다. 처음에 번역기 돌려가면서 잘 모르는 상태에 시도했다가 뭔가 꼬였는데 깃헙리포 url이 박제된건지 같은 url에선 
재등록도 안되는 상태가 되서 이름까지 바꿨습니다. 또 바꾸긴 싫으니 설명서 좀 잘 읽어보고 다시 시도 할 생각입니다.

<br>

## 3. 노드 소개
  ### - Linsoo Save Image
  ![스크린샷 2025-01-15 150752](https://image.linsoo.pe.kr/linsoosaveimage-2025-01-26-204620.webp)
  파일 저장시 jpg와 webp를 추가한 커스텀 노드입니다.
  #### 사용법
  **filename_prefix** : 저장 파일명 형식을 지정할 수 있습니다. 지원되는 변수는 아래와 같습니다.
  
    - 날짜, 시간 : %date:yyyy-MM-dd hh-mm-ss%
    - 체크 포인트 이름, 해쉬값 : %ckpt%, %ckpt_hash%
    - 샘플러 정보 : %seed%, %steps%, %cfg%, %sampler_name%, %scheduler%
    - 캐릭터 이름 : %character_name%
    
    예시1) /%date:YYYY%년/%date:MM%월/%ckpt%_[%ckpt_hash%]/%date:YYYYMMDD_hhmmss%_%ckpt%
    결과1) /2025년/01월/noobaiXLNAIXL_vPred10Version_[ea349eeae8]/20250113_215923_noobaiXLNAIXL_vPred10Version.webp
    
    예시2) %character_name%_%date:YYYYMMDD_hhmmss%
    결과2) marcille donato_20250113_215923.webp

    캐릭터 이름은 (https://huggingface.co/datasets/Laxhar/noob-wiki/tree/main) 에 있는 danbooru_character.csv 파일 trigger 항목을 사용합니다.
   
  **file_type** : jpg, webp, png 형식으로 저장 할 수 있습니다.

  **quality** : jpg, webp의 화질을 설정하는 값이며 -1을 입력할 경우 webp는 무손실 방식으로 저장되고 jpg는 0으로 대체됩니다. 
  1~100의 구간은 webp, jpg 둘다 손실 압축으로 저장되며 기본값은 90입니다. 
  png의 경우 해당 옵션에 영향을 받지 않습니다.
  
  **meta_save_type** : 메타 저장 형식에 대한 옵션이며 각 항목은 아래와 같습니다.

    - None : EXIF 정보를 저장하지 않습니다.
    - A1111 WebUI (webp,png) : stable-diffusion-webui 과 유사한 형식으로 저장합니다. (webp,jpg 형식에서 사용할 수 있습니다)    
    - ComfyUI (webp,png) : ComfyUI 기본 형식으로 저장합니다. (webp,png 형식에서 사용할 수 있습니다)
  
  ![civitai 호환이미지](https://image.linsoo.pe.kr/civitai-2025-01-26-204709.webp)
  Civitai.com에 업로드시 프롬프트를 자동인식 하게 할려면 <span style="color:red">png+Comfy, jpg+a1111, webp+a1111</span> 방식으로 저장을 해야 합니다.

  
  ### - Linsoo Empty Latent Image
  ![스크린샷 2025-01-15 210313](https://github.com/user-attachments/assets/0fcd9ca2-755d-46ec-88d9-a91a81a94fb1)
  추천 이미지 사이즈 목록입니다. 많이 쓰는 이미지 해상도를 선택하면 됩니다.
  <br>

  ### - Linsoo Multi Input Output
  ![스크린샷 2025-01-21 205425](https://github.com/user-attachments/assets/4c18eee0-d4b2-4a03-9c18-d3cfd5136523)
  여러 그룹간에 연결을 간편하게 할려고 만든 노드.
    - multi inputs :  8개 입력을 1라인으로 출력
    - multi outputs : 1개 입력을 8라인으로 출력


## 4. 기타...

>[!IMPORTANT]
>이 노드 사용시 output 폴더에 extra_pnginfo.json, prompt.json 파일이 생깁니다. 에러 발생시 이 두 파일을 같이 올려주시면 디버깅에 큰 도움이 됩니다.

블로그 : https://linsoo.pe.kr
버전 : 1.2.2