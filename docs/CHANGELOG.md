# Changelog

## v0.0.3
`2025.11.30 12:00`

프로젝트별 region 및 IAM role 설정 지원

- `projects.yml`에 `region`, `aws.ecr_role`, `aws.instance_role` 필드 추가
- GitHub Secrets에서 `AWS_ACCOUNT_ID`만 사용, role ARN은 동적 조합
- 배포 단순화: `start-deployment`만 호출 (마이그레이션 로직 제거)
- 불필요한 secrets 정리: `AWS_REGION`, `APP_RUNNER_*_ROLE_ARN` 삭제

---

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
