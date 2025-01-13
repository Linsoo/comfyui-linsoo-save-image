# ComfyUI-Linsoo-Save-Image
파일 저장시 jpg와 webp를 추가한 커스텀 노드입니다.

![스크린샷 2025-01-13 221406](https://github.com/user-attachments/assets/cf024a83-967b-4ee1-b497-c36c0bcb5c93)

## 차이점
- 파일명에 사용할 수 있는 변수 추가
- EXIF 저장 형식을  지정할 수 있습니다.


## 사용법
![스크린샷 2025-01-13 221406_수정버전](https://github.com/user-attachments/assets/4410c9be-1347-40d4-82ce-99e842d6730c)

### 1번 filename_prefix
저장 파일명 형식을 지정할 수 있습니다.
지원되는 변수는 아래와 같습니다.
  - 날짜, 시간 : %date:yyyy-MM-dd hh-mm-ss%
  - 체크 포인트 이름, 해쉬값 : %ckpt%, %ckpt_hash%
  - 샘플러 정보 : %seed%, %steps%, %cfg%, %sampler_name%, %scheduler%
  - 캐릭터 이름 : %character_name%

예시1) /%date:YYYY%년/%date:MM%월/%ckpt%_[%ckpt_hash%]/%date:YYYYMMDD_hhmmss%_%ckpt% <br>
결과1) /2025년/01월/noobaiXLNAIXL_vPred10Version_[ea349eeae8]/20250113_215923_noobaiXLNAIXL_vPred10Version.webp

예시2) %character_name%_%date:YYYYMMDD_hhmmss% <br>
결과2) marcille donato_20250113_215923.webp

캐릭터 이름은 (https://huggingface.co/datasets/Laxhar/noob-wiki/tree/main) 에 있는 danbooru_character.csv 파일 trigger 항목을 사용합니다.

### 2번 exif_format
EXIF Comment 영역에 기록할 내용 형식을 지정할 수 있습니다.
지원되는 변수는 아래와 같습니다.
  - 이미지 사이즈 : %width%, %height%
  - 체크 포인트 이름, 해쉬값 : %ckpt%, %ckpt_hash%
  - 샘플러 정보 : %seed%, %steps%, %cfg%, %sampler_name%, %scheduler%, %denoise%
  - Clip Skip : %clipskip%
  - 프롬프트 :  %positive%, %negative%
  - 로라 목록(로라이름:해쉬값) : %loras%


### 3번 file_type
jpg, webp, png 형식으로 저장 할 수 있으며 png 형식은 2번 exif_format이 적용되지 않습니다. (기존의 ComfyUI에서 저장하던 방식 그대로 저장됩니다)


### 4번 quality
quality는 저장 화질을 설정하는 값이며 -1, 1 ~ 100 의 구간을 가집니다. (기본값은 90입니다)
-1로 설정할 경우 무손실 저장방식이 적용됩니다.


### 5번 meta_type
- None : EXIF 정보를 저장하지 않습니다.
- Image(include exif) : exif_format 의 값을 EXIF.Comment 란에 저장하고 workflow는 idf 영역에 저장합니다. (webp의 경우 ComfyUI에 드래그 앤 드롭을 하면 workflow를 볼 수 있습니다.)
- Image(include exif)+Workflow.json : 이미지에 exif+workflow를 저장하고 별도의 json 파일에 workflow를 저장합니다. (jpg에 workflow 정보를 저장해도 ComfyUI에서 불러오지 못하기 때문에 별도의 json 파일을 생성하는 옵션을 넣었습니다)



>[!IMPORTANT]
>이 노드 사용시 output 폴더에 extra_pnginfo.json, prompt.json 파일이 생깁니다. 에러 발생시 이 두 파일을 같이 올려주시면 디버깅에 큰 도움이 됩니다.

블로그 : https://linsoo.pe.kr



    
