# Changelog

## v0.0.2
`2025.11.29 22:22`

Secrets Manager 동적 주입 리팩토링

- `production/{project}` 컨벤션으로 자동 secret 탐색
- `spring.mongodb.uri` → `SPRING_MONGODB_URI` 자동 변환
- stash.yml에서 secrets 설정 제거 (코드 변경 없이 secret 추가 가능)

---

## v0.0.1
`2025.11.29 20:58`

deployment-hub 초기 구성

- App Runner 배포 workflow 추가
- stash 프로젝트 설정 추가
- GitHub Deployment, Release 자동 생성

---
