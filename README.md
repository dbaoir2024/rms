# 🏢 Organizational Information and Regulatory Records Management System (OIRRMS)

A comprehensive Flask-based system for managing organizational data, elections, and regulatory compliance with robust access control.

## 🔧 Core Architecture
- **Flask**-based REST API with **PostgreSQL** backend
- **JWT authentication** with role-based access control
- Comprehensive error handling and CORS configuration

## 🧩 Key Functional Modules

### 👥 User Management
- Role-based access control with permissions
- User profiles with positions
- Authentication (email/password + Google OAuth)

### 🏛 Organization Management
- Organization profiles with types and statuses
- Officials management
- Constitution version control
- Geographic hierarchy (regions/districts)

### 🗳 Election Management
- Ballot elections tracking
- Positions and candidates management
- Vote results recording

### 📋 Compliance Management
- Regulatory requirements tracking
- Compliance records with deadlines
- Inspections and findings
- Non-compliance issue resolution

## ⚙️ Technical Features
- UUID primary keys for all entities
- Audit fields (created_at, updated_at) throughout
- Comprehensive serialization (to_dict methods)
- Pagination and filtering on all list endpoints
- Date handling with proper validation
- Document attachment support

## 🌐 API Design
- RESTful endpoints with proper HTTP verbs
- Consistent response structure (success, data, message)
- Detailed error handling (400, 401, 403, 404, 500)
- Token-based authentication for all endpoints

## 🗃 Data Model Highlights
- Flexible role/permission system
- Organization hierarchy with types
- Election process modeling (elections → positions → candidates → results)
- Compliance workflow (requirements → records → inspections → issues)

💡 The system features clear separation of concerns between models, routes, and business logic, following REST best practices for managing organizational information and regulatory compliance.
