# CLAUDE.md — Backend

> 이 파일은 Claude Code가 프로젝트 컨텍스트를 이해하기 위한 파일입니다.
> 해커톤 전용 설정이므로, 속도와 완성도를 최우선으로 합니다.

---

## 프로젝트 개요

- **목적**: 해커톤 백엔드 프로젝트
- **주제**: 미정 (확정 시 Agent.md에 추가 예정)
- **개발 기간**: 해커톤 당일 (단기 집중 개발)
- **팀 규모**: 4명

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| Framework | Spring Boot 4.0.6 |
| Language | Java 21 |
| ORM | Spring Data JPA + Hibernate |
| Database | (미정 - 클라우드 DB 사용 예정) |
| 인증 | Spring Security + JWT |
| 빌드 | Gradle |
| 배포 | Railway (GitHub main 브랜치 자동 배포) |
| API 문서 | Swagger (springdoc-openapi) |

---

## 아키텍처

**계층형 아키텍처 (Layered Architecture)** 사용
헥사고날, DDD 등 복잡한 아키텍처는 해커톤 범위에서 적용하지 않습니다.

```
com.{팀명}.{프로젝트명}
├── controller/       # API 엔드포인트, 요청/응답 처리
├── service/          # 비즈니스 로직
├── repository/       # DB 접근 (JPA Repository)
├── domain/
│   ├── entity/       # JPA Entity
│   └── dto/          # Request / Response DTO
├── config/           # Security, Swagger, CORS 등 설정
├── exception/        # 커스텀 예외, 전역 예외 처리
└── util/             # 유틸 클래스
```

---

## 코드 컨벤션

### 네이밍
- **클래스**: PascalCase → `UserController`, `UserService`
- **메서드/변수**: camelCase → `getUserById`, `userName`
- **상수**: UPPER_SNAKE_CASE → `JWT_SECRET_KEY`
- **패키지**: 소문자 → `com.teamname.project.controller`

### Controller
- URL은 소문자 + 하이픈 → `/api/user-profiles`
- RESTful 규칙 준수 (GET/POST/PUT/DELETE)
- 비즈니스 로직은 Controller에 작성하지 않음
- 응답은 공통 `ApiResponse<T>` 래퍼 클래스 사용

```java
// ✅ Good
@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<UserResponse>> getUser(@PathVariable Long id) {
        return ResponseEntity.ok(ApiResponse.success(userService.getUser(id)));
    }
}
```

### Service
- 하나의 메서드는 하나의 책임만
- `@Transactional` 적절히 사용 (조회는 `readOnly = true`)

```java
// ✅ Good
@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;

    @Transactional(readOnly = true)
    public UserResponse getUser(Long id) {
        User user = userRepository.findById(id)
            .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
        return UserResponse.from(user);
    }
}
```

### DTO
- Request / Response DTO 분리
- Entity를 직접 반환하지 않음 (DTO로 변환 필수)
- 변환 메서드는 DTO 내부에 정적 팩토리 메서드로 작성

```java
// ✅ Good
public record UserResponse(Long id, String name, String email) {
    public static UserResponse from(User user) {
        return new UserResponse(user.getId(), user.getName(), user.getEmail());
    }
}
```

### 예외 처리
- 커스텀 예외는 `CustomException` 하나로 통일, `ErrorCode` enum으로 관리
- `@RestControllerAdvice`로 전역 처리

```java
// ErrorCode.java
@Getter
@RequiredArgsConstructor
public enum ErrorCode {
    USER_NOT_FOUND(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."),
    INVALID_TOKEN(HttpStatus.UNAUTHORIZED, "유효하지 않은 토큰입니다.");

    private final HttpStatus status;
    private final String message;
}
```

### 공통 응답 형식
모든 API 응답은 아래 형식으로 통일합니다.

```json
// 성공
{
  "success": true,
  "data": { ... }
}

// 실패
{
  "success": false,
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "사용자를 찾을 수 없습니다."
  }
}
```

---

## 버전 관리

- 의존성 버전은 `build.gradle` 상단 `ext` 블록에 변수로 고정
- 임의로 버전 올리지 않음, 변경 시 팀원과 합의 후 수정

```groovy
// build.gradle
ext {
    jwtVersion = '0.11.5'
    swaggerVersion = '2.3.0'
}
```

---

## 테스트 정책

- 해커톤 기간 중 단위 테스트 작성은 하지 않음
- 빠른 빌드 확인 (테스트 제외): `./gradlew build -x test`
- API 동작 확인은 **Swagger UI로 수동 테스트**
- 배포 전 최소 1회 전체 빌드 확인 권장: `./gradlew build`

---

## 브랜치 전략

```
main         ← Railway 자동 배포 (직접 push 금지)
dev          ← 통합 브랜치 (PR 후 머지)
{이름}       ← 개인 작업 브랜치 (예: jihun, gildong)
```

### 규칙
1. **개인 브랜치 → dev** PR 후 머지
2. **dev → main** 은 배포 준비 완료 시점에만 머지
3. 큰 기능이 dev에 머지될 때마다 **개인 브랜치에 dev를 머지해서 싱크 유지**
4. main에 직접 push 절대 금지

---

## 배포 환경

- **플랫폼**: Railway
- **자동 배포**: `main` 브랜치 push 시 자동 배포
- **환경변수**: Railway 대시보드에서 관리 (로컬 `application-local.yml` 사용)
- **포트**: `8080`

### 환경 분리
```
application.yml          # 공통 설정
application-local.yml    # 로컬 개발용 (gitignore 처리)
application-prod.yml     # 운영 환경 (Railway 환경변수로 주입)
```

---

## CORS 설정

프론트엔드 Vercel 도메인에 대해 CORS를 허용합니다.
로컬 개발 시 `http://localhost:3000`도 허용.

```java
@Configuration
public class CorsConfig implements WebMvcConfigurer {
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
            .allowedOrigins(
                "http://localhost:3000",
                "https://{vercel-domain}.vercel.app"  // 실제 도메인으로 교체
            )
            .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
            .allowCredentials(true);
    }
}
```

---

## 해커톤 필수 주의사항

### 하지 말아야 할 것 ❌
- 헥사고날 아키텍처, DDD, MSA 등 복잡한 설계 패턴 도입
- Docker / 컨테이너 환경 구성 (Railway가 알아서 처리)
- 인터페이스를 구현체가 하나인데 억지로 분리
- 지나친 추상화 (지금 당장 쓰이지 않는 코드 작성 금지)
- 성능 최적화 (캐싱, 쿼리 튜닝 등) — MVP 완성 후에 고민
- Lombok 없이 보일러플레이트 코드 수동 작성

### 우선순위 ✅
1. 핵심 API 엔드포인트 동작 여부
2. 프론트엔드 연동 완료
3. 예외 처리 기본 세팅
4. 나머지 디테일

---

## 자주 쓰는 명령어

```bash
# 빌드
./gradlew build

# 빌드 (테스트 제외 — 해커톤 중 빠른 빌드용)
./gradlew build -x test

# 로컬 실행
./gradlew bootRun --args='--spring.profiles.active=local'

# 의존성 확인
./gradlew dependencies
```

---

## API 문서

- 로컬: `http://localhost:8080/swagger-ui.html`
- 배포: `https://{railway-domain}/swagger-ui.html`
- API 변경 시 Swagger 어노테이션 업데이트 필수

---

## 참고

- 프론트엔드 레포: `team-frontend`
- API 명세: Swagger 또는 Notion 참고
- 디자인 시안: Figma 링크 (추후 업데이트)
- 문의: GitHub Issues 또는 Discord

## 성과 문서화
팀장이 "문서화해줘"라고 요청하면 @docs/DOCS_GUIDE.md 를 참조해서 정리하세요.
